"""
Exportador de dados
Gera arquivos CSV e Excel com os dados coletados
"""

import os
import csv
import logging
from datetime import datetime
from typing import List, Dict
import pandas as pd

logger = logging.getLogger(__name__)


class DataExporter:
    """Exporta dados do crawler para CSV e Excel"""
    
    def __init__(self, config: dict):
        self.config = config.get('export', {})
        self.output_folder = self.config.get('output_folder', 'output')
        self.filename_prefix = self.config.get('filename_prefix', 'crawl')
        self.include_timestamp = self.config.get('include_timestamp', True)
        self.export_format = self.config.get('format', 'both')
        self.fields = self.config.get('fields', [])
        
        # Cria pasta de output se não existir
        os.makedirs(self.output_folder, exist_ok=True)
    
    def export(self, data: List[Dict], stats: Dict = None) -> List[str]:
        """
        Exporta dados para arquivo(s)
        
        Args:
            data: Lista de dicionários com dados das URLs
            stats: Estatísticas do crawl (opcional)
        
        Returns:
            Lista de caminhos dos arquivos gerados
        """
        if not data:
            logger.warning("Nenhum dado para exportar")
            return []
        
        # Prepara DataFrame
        df = self._prepare_dataframe(data)
        
        # Gera nome base do arquivo
        base_filename = self._generate_filename()
        
        exported_files = []
        
        # Exporta conforme formato configurado
        if self.export_format in ['csv', 'both']:
            csv_file = self._export_csv(df, base_filename)
            if csv_file:
                exported_files.append(csv_file)
        
        if self.export_format in ['xlsx', 'both']:
            xlsx_file = self._export_xlsx(df, base_filename, stats)
            if xlsx_file:
                exported_files.append(xlsx_file)
        
        return exported_files
    
    def _prepare_dataframe(self, data: List[Dict]) -> pd.DataFrame:
        """Prepara DataFrame com os dados"""
        df = pd.DataFrame(data)
        
        # Reordena colunas conforme configurado
        if self.fields:
            # Mantém apenas campos configurados (que existem no DataFrame)
            available_fields = [f for f in self.fields if f in df.columns]
            
            # Adiciona campos que não estão na configuração mas existem no DataFrame
            extra_fields = [col for col in df.columns if col not in available_fields]
            
            # Reordena
            ordered_columns = available_fields + extra_fields
            df = df[ordered_columns]
        
        return df
    
    def _generate_filename(self) -> str:
        """Gera nome base do arquivo"""
        filename = self.filename_prefix
        
        if self.include_timestamp:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{filename}_{timestamp}"
        
        return filename
    
    def _export_csv(self, df: pd.DataFrame, base_filename: str) -> str:
        """Exporta para CSV"""
        try:
            filepath = os.path.join(self.output_folder, f"{base_filename}.csv")
            
            df.to_csv(
                filepath,
                index=False,
                encoding='utf-8-sig',  # UTF-8 com BOM para Excel
                quoting=csv.QUOTE_ALL
            )
            
            logger.info(f"✅ CSV exportado: {filepath} ({len(df)} linhas)")
            return filepath
            
        except Exception as e:
            logger.error(f"Erro ao exportar CSV: {e}")
            return None
    
    def _export_xlsx(self, df: pd.DataFrame, base_filename: str, stats: Dict = None) -> str:
        """Exporta para Excel com múltiplas abas"""
        try:
            filepath = os.path.join(self.output_folder, f"{base_filename}.xlsx")
            
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # Aba principal com dados
                df.to_excel(
                    writer,
                    sheet_name='Crawl Data',
                    index=False,
                    freeze_panes=(1, 0)  # Congela primeira linha
                )
                
                # Formata aba principal
                worksheet = writer.sheets['Crawl Data']
                self._format_worksheet(worksheet, df)
                
                # Aba de resumo
                if stats:
                    summary_df = self._create_summary_df(df, stats)
                    summary_df.to_excel(
                        writer,
                        sheet_name='Summary',
                        index=False
                    )
                
                # Aba de issues (se houver)
                issues_df = self._create_issues_df(df)
                if not issues_df.empty:
                    issues_df.to_excel(
                        writer,
                        sheet_name='Issues',
                        index=False
                    )
            
            logger.info(f"✅ Excel exportado: {filepath} ({len(df)} linhas)")
            return filepath
            
        except Exception as e:
            logger.error(f"Erro ao exportar Excel: {e}")
            return None
    
    def _format_worksheet(self, worksheet, df: pd.DataFrame):
        """Formata planilha Excel"""
        try:
            # Ajusta largura das colunas
            for idx, col in enumerate(df.columns, 1):
                # Calcula largura baseado no conteúdo
                max_length = max(
                    df[col].astype(str).apply(len).max(),
                    len(str(col))
                )
                adjusted_width = min(max_length + 2, 50)  # Máximo 50
                
                column_letter = worksheet.cell(row=1, column=idx).column_letter
                worksheet.column_dimensions[column_letter].width = adjusted_width
            
            # Formata cabeçalho
            for cell in worksheet[1]:
                cell.font = cell.font.copy(bold=True)
                cell.fill = cell.fill.copy(fgColor="D3D3D3")
            
        except Exception as e:
            logger.warning(f"Erro ao formatar planilha: {e}")
    
    def _create_summary_df(self, df: pd.DataFrame, stats: Dict) -> pd.DataFrame:
        """Cria DataFrame de resumo"""
        summary_data = []
        
        # Estatísticas gerais
        summary_data.append(['Total URLs', len(df)])
        summary_data.append(['URLs Indexáveis', df['indexable'].sum() if 'indexable' in df else 0])
        summary_data.append(['URLs Não-Indexáveis', len(df) - df['indexable'].sum() if 'indexable' in df else 0])
        summary_data.append(['', ''])
        
        # Detalhamento de URLs não-indexáveis por motivo
        if 'indexable' in df:
            non_indexable = df[~df['indexable']]
            if len(non_indexable) > 0:
                summary_data.append(['Páginas Não-Indexáveis por Motivo', ''])
                
                # Páginas com noindex
                noindex_count = len(non_indexable[non_indexable.get('robots_noindex', False)])
                if noindex_count > 0:
                    summary_data.append(['  Meta robots noindex', noindex_count])
                
                # Páginas com canonical diferente
                canonical_diff = 0
                if 'canonical' in df.columns and 'url' in df.columns:
                    canonical_diff = len(non_indexable[
                        (non_indexable['canonical'] != '') & 
                        (non_indexable['canonical'] != non_indexable['url'])
                    ])
                if canonical_diff > 0:
                    summary_data.append(['  Canonical apontando para outra URL', canonical_diff])
                
                # Páginas com noindex + canonical (problema duplo)
                if noindex_count > 0 and canonical_diff > 0:
                    double_issue = len(non_indexable[
                        (non_indexable.get('robots_noindex', False)) &
                        (non_indexable['canonical'] != '') & 
                        (non_indexable['canonical'] != non_indexable['url'])
                    ])
                    if double_issue > 0:
                        summary_data.append(['  Noindex + Canonical diferente', double_issue])
                
                summary_data.append(['', ''])
        
        # Status codes
        if 'status_code' in df:
            summary_data.append(['Status Codes', ''])
            status_counts = df['status_code'].value_counts().sort_index()
            for status, count in status_counts.items():
                summary_data.append([f'  {status}', count])
            summary_data.append(['', ''])
        
        # Tipos de conteúdo
        if 'content_type' in df:
            summary_data.append(['Content Types', ''])
            type_counts = df['content_type'].value_counts()
            for content_type, count in type_counts.items():
                summary_data.append([f'  {content_type}', count])
            summary_data.append(['', ''])
        
        # Issues
        summary_data.append(['Issues Detectados', ''])
        
        if 'title_length' in df:
            short_titles = len(df[df['title_length'] < 30])
            long_titles = len(df[df['title_length'] > 60])
            missing_titles = len(df[df['title_length'] == 0])
            if missing_titles > 0:
                summary_data.append(['  Títulos faltando', missing_titles])
            if short_titles > 0:
                summary_data.append(['  Títulos muito curtos (<30)', short_titles])
            if long_titles > 0:
                summary_data.append(['  Títulos muito longos (>60)', long_titles])
        
        if 'meta_description_length' in df:
            missing_desc = len(df[df['meta_description_length'] == 0])
            short_desc = len(df[(df['meta_description_length'] > 0) & (df['meta_description_length'] < 120)])
            long_desc = len(df[df['meta_description_length'] > 160])
            if missing_desc > 0:
                summary_data.append(['  Meta descriptions faltando', missing_desc])
            if short_desc > 0:
                summary_data.append(['  Meta descriptions curtas (<120)', short_desc])
            if long_desc > 0:
                summary_data.append(['  Meta descriptions longas (>160)', long_desc])
        
        if 'h1_count' in df:
            missing_h1 = len(df[df['h1_count'] == 0])
            multiple_h1 = len(df[df['h1_count'] > 1])
            if missing_h1 > 0:
                summary_data.append(['  H1 faltando', missing_h1])
            if multiple_h1 > 0:
                summary_data.append(['  Múltiplos H1', multiple_h1])
        
        if 'images_without_alt' in df:
            total_images_without_alt = df['images_without_alt'].sum()
            pages_with_missing_alt = len(df[df['images_without_alt'] > 0])
            if total_images_without_alt > 0:
                summary_data.append(['  Total de imagens sem ALT', int(total_images_without_alt)])
                summary_data.append(['  Páginas com imagens sem ALT', pages_with_missing_alt])
        
        # Estatísticas de padrões de URL
        if stats and 'pattern_stats' in stats:
            summary_data.append(['', ''])
            summary_data.append(['Limites por Padrão de URL', ''])
            
            for description, pattern_stats in stats['pattern_stats'].items():
                count = pattern_stats['count']
                limit = pattern_stats['limit']
                percentage = pattern_stats['percentage']
                summary_data.append([
                    f"  {description}",
                    f"{count}/{limit} ({percentage:.1f}%)"
                ])
        
        # Estatísticas de crawl
        if stats:
            summary_data.append(['', ''])
            summary_data.append(['Estatísticas de Crawl', ''])
            summary_data.append(['  Duração', stats.get('duration', 'N/A')])
            summary_data.append(['  URLs/segundo', f"{stats.get('urls_per_second', 0):.2f}"])
            summary_data.append(['  Tempo médio de resposta', f"{stats.get('avg_response_time', 0):.3f}s"])
        
        return pd.DataFrame(summary_data, columns=['Métrica', 'Valor'])
    
    def _create_issues_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cria DataFrame com issues detectados"""
        issues = []
        
        for idx, row in df.iterrows():
            url = row.get('url', '')
            
            # Indexabilidade - PRIORIDADE ALTA
            if 'indexable' in row and not row['indexable']:
                reasons = []
                severity = 'High'
                
                # Identifica os motivos específicos
                if row.get('robots_noindex', False):
                    reasons.append('meta robots noindex')
                
                if row.get('canonical', '') and row['canonical'] != url:
                    reasons.append(f'canonical aponta para {row["canonical"]}')
                
                # Se ambos, é crítico
                if len(reasons) > 1:
                    severity = 'Critical'
                
                if reasons:
                    issues.append({
                        'url': url,
                        'issue_type': 'Indexability',
                        'issue': f'Página não-indexável: {" | ".join(reasons)}',
                        'severity': severity,
                        'detail': ', '.join(reasons)
                    })
            
            # Títulos
            if 'title_length' in row:
                if row['title_length'] == 0:
                    issues.append({
                        'url': url,
                        'issue_type': 'Title',
                        'issue': 'Título faltando',
                        'severity': 'High',
                        'detail': 'Nenhum título definido'
                    })
                elif row['title_length'] < 30:
                    issues.append({
                        'url': url,
                        'issue_type': 'Title',
                        'issue': f'Título muito curto ({row["title_length"]} caracteres)',
                        'severity': 'Medium',
                        'detail': f'Título atual: "{row.get("title", "")}"'
                    })
                elif row['title_length'] > 60:
                    issues.append({
                        'url': url,
                        'issue_type': 'Title',
                        'issue': f'Título muito longo ({row["title_length"]} caracteres)',
                        'severity': 'Medium',
                        'detail': f'Título será truncado nos resultados de busca'
                    })
            
            # Meta Description
            if 'meta_description_length' in row:
                if row['meta_description_length'] == 0:
                    issues.append({
                        'url': url,
                        'issue_type': 'Meta Description',
                        'issue': 'Meta description faltando',
                        'severity': 'High',
                        'detail': 'Google pode gerar descrição automaticamente'
                    })
                elif row['meta_description_length'] < 120:
                    issues.append({
                        'url': url,
                        'issue_type': 'Meta Description',
                        'issue': f'Meta description muito curta ({row["meta_description_length"]} caracteres)',
                        'severity': 'Medium',
                        'detail': 'Ideal: 120-160 caracteres'
                    })
                elif row['meta_description_length'] > 160:
                    issues.append({
                        'url': url,
                        'issue_type': 'Meta Description',
                        'issue': f'Meta description muito longa ({row["meta_description_length"]} caracteres)',
                        'severity': 'Low',
                        'detail': 'Será truncada nos resultados de busca'
                    })
            
            # H1
            if 'h1_count' in row:
                if row['h1_count'] == 0:
                    issues.append({
                        'url': url,
                        'issue_type': 'H1',
                        'issue': 'H1 faltando',
                        'severity': 'High',
                        'detail': 'Toda página deve ter exatamente 1 H1'
                    })
                elif row['h1_count'] > 1:
                    issues.append({
                        'url': url,
                        'issue_type': 'H1',
                        'issue': f'Múltiplos H1 ({row["h1_count"]})',
                        'severity': 'Medium',
                        'detail': 'Páginas devem ter apenas 1 H1'
                    })
            
            # Imagens sem ALT
            if 'images_without_alt' in row and row['images_without_alt'] > 0:
                issues.append({
                    'url': url,
                    'issue_type': 'Images',
                    'issue': f'{int(row["images_without_alt"])} imagem(ns) sem ALT text',
                    'severity': 'Medium',
                    'detail': 'ALT text é importante para acessibilidade e SEO'
                })
            
            # Canonical para si mesmo ausente (se tiver canonical vazio em página indexável)
            if row.get('indexable', False) and row.get('canonical', '') == '':
                issues.append({
                    'url': url,
                    'issue_type': 'Canonical',
                    'issue': 'Canonical tag ausente',
                    'severity': 'Low',
                    'detail': 'Recomendado ter canonical apontando para si mesmo'
                })
        
        if not issues:
            return pd.DataFrame()
        
        # Ordena por severidade
        severity_order = {'Critical': 0, 'High': 1, 'Medium': 2, 'Low': 3}
        issues_df = pd.DataFrame(issues)
        issues_df['severity_order'] = issues_df['severity'].map(severity_order)
        issues_df = issues_df.sort_values(['severity_order', 'issue_type', 'url'])
        issues_df = issues_df.drop('severity_order', axis=1)
        
        return issues_df
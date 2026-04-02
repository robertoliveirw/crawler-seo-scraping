"""
SEO Crawler - Motor principal
Crawler SEO customizado com limites por padrão de URL
"""

import requests
import logging
import time
import yaml
from collections import deque, defaultdict
from typing import Set, Dict, List, Optional, Tuple
from urllib.parse import urlparse, urljoin
from datetime import datetime
from tqdm import tqdm
from colorama import Fore, Style, init

from utils import (
    RateLimiter, RobotsTxtChecker, URLPatternMatcher,
    URLNormalizer, DirectoryCounter, format_duration
)
from extractors import SEODataExtractor
from exporters import DataExporter

# Inicializa colorama
init(autoreset=True)

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class SEOCrawler:
    """Crawler SEO com suporte a limites por padrão de URL"""
    
    def __init__(self, config_path: str = 'config.yaml'):
        """
        Inicializa o crawler
        
        Args:
            config_path: Caminho para arquivo de configuração YAML
        """
        # Carrega configuração
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.start_url = self.config['start_url']
        self.crawl_config = self.config.get('crawl', {})
        
        # Componentes
        self.rate_limiter = RateLimiter(
            self.config['rate_limiting']['requests_per_second'],
            tuple(self.config['rate_limiting']['random_delay_range'])
        )
        
        self.robots_checker = None
        if self.config.get('respect_robots_txt', True):
            self.robots_checker = RobotsTxtChecker(self.config['user_agent'])
        
        self.pattern_matcher = URLPatternMatcher(self.config)
        self.extractor = SEODataExtractor(self.config)
        self.exporter = DataExporter(self.config)
        self.directory_counter = DirectoryCounter(
            self.config['safety']['max_urls_per_directory']
        )
        
        # Estado do crawl
        self.visited: Set[str] = set()
        self.to_crawl: deque = deque()
        self.crawled_data: List[Dict] = []
        self.url_depth: Dict[str, int] = {}
        self.url_source: Dict[str, Tuple[str, str]] = {}  # URL -> (fonte, anchor)
        
        # Estatísticas
        self.stats = {
            'start_time': None,
            'end_time': None,
            'total_urls': 0,
            'urls_crawled': 0,
            'urls_skipped': 0,
            'urls_failed': 0,
            'status_codes': defaultdict(int),
            'response_times': []
        }
        
        # Session HTTP
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Cria sessão HTTP com configurações"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': self.config['user_agent'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
        
        # Desabilita verificação SSL para evitar erros de certificado
        session.verify = False
        
        # Suprime warnings de SSL
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Configura retries
        from requests.adapters import HTTPAdapter
        try:
            # Tenta importar do requests (versões antigas)
            from requests.packages.urllib3.util.retry import Retry
        except ImportError:
            # Importa diretamente do urllib3 (versões novas)
            from urllib3.util.retry import Retry
        
        retry_config = Retry(
            total=self.config['rate_limiting']['max_retries'],
            backoff_factor=self.config['rate_limiting']['retry_backoff'],
            status_forcelist=[429, 500, 502, 503, 504]
        )
        
        adapter = HTTPAdapter(max_retries=retry_config)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        return session
    
    def crawl(self):
        """Inicia o processo de crawling"""
        logger.info(f"\n{Fore.CYAN}{'='*80}")
        logger.info(f"{Fore.CYAN}🚀 Iniciando SEO Crawler")
        logger.info(f"{Fore.CYAN}{'='*80}\n")
        
        logger.info(f"📍 URL inicial: {Fore.GREEN}{self.start_url}")
        logger.info(f"🔧 Configuração carregada: {Fore.GREEN}config.yaml\n")
        
        self.stats['start_time'] = time.time()
        
        # Adiciona URL inicial à fila
        self._add_to_queue(self.start_url, depth=0, source='start', anchor='')
        
        # Barra de progresso
        max_urls = self.crawl_config.get('max_total_urls', 0)
        progress_bar = None
        
        if self.config['logging']['show_progress_bar'] and max_urls > 0:
            progress_bar = tqdm(
                total=max_urls,
                desc="Crawling",
                unit="URLs",
                colour='green'
            )
        
        try:
            # Loop principal de crawl
            while self.to_crawl:
                url, depth = self.to_crawl.popleft()
                
                # Verifica limites
                if not self._should_continue_crawl():
                    logger.info(f"\n{Fore.YELLOW}⚠️  Limite de crawl atingido")
                    break
                
                # Crawla URL
                success = self._crawl_url(url, depth)
                
                if success:
                    self.stats['urls_crawled'] += 1
                else:
                    self.stats['urls_failed'] += 1
                
                # Atualiza progresso
                if progress_bar:
                    progress_bar.update(1)
                    progress_bar.set_postfix({
                        'Fila': len(self.to_crawl),
                        'Erros': self.stats['urls_failed']
                    })
            
            if progress_bar:
                progress_bar.close()
            
        except KeyboardInterrupt:
            logger.warning(f"\n{Fore.YELLOW}⚠️  Crawl interrompido pelo usuário")
        
        finally:
            self._finalize_crawl()
    
    def _crawl_url(self, url: str, depth: int) -> bool:
        """
        Crawla uma URL específica
        
        Args:
            url: URL a ser crawlada
            depth: Profundidade atual
        
        Returns:
            True se sucesso, False se falha
        """
        try:
            # Rate limiting
            self.rate_limiter.wait()
            
            # Faz requisição SEM seguir redirects automaticamente
            start_time = time.time()
            response = self.session.get(
                url,
                timeout=self.config['rate_limiting']['request_timeout'],
                allow_redirects=False  # Mudado para rastrear redirects manualmente
            )
            response_time = time.time() - start_time
            
            self.stats['response_times'].append(response_time)
            
            status_code = response.status_code
            self.stats['status_codes'][status_code] += 1
            
            # Detecta e processa redirect chains
            redirect_chain = []
            final_url = url
            
            if status_code in [301, 302, 303, 307, 308]:
                redirect_chain, final_url, final_status = self._follow_redirect_chain(url, response)
                # Atualiza status code para o final
                if final_status:
                    status_code = final_status
            
            # Log conforme status
            if status_code == 200:
                logger.debug(f"✅ {status_code} - {url}")
            elif status_code in [301, 302, 307, 308]:
                logger.debug(f"↪️  {status_code} - {url}")
            elif status_code == 404:
                logger.warning(f"❌ {status_code} - {url}")
            else:
                logger.warning(f"⚠️  {status_code} - {url}")
            
            # Extrai dados
            data = self.extractor.extract(
                response.text,
                url,
                response_time
            )
            
            # Adiciona metadados
            data['status_code'] = status_code
            data['crawl_depth'] = depth
            
            # Adiciona informações de redirect chain
            if redirect_chain:
                data['redirect_chain'] = ' -> '.join(redirect_chain)
                data['redirect_hops'] = len(redirect_chain) - 1
                data['final_destination'] = final_url
                data['has_redirect_chain'] = len(redirect_chain) > 2  # Mais de 1 hop
                data['redirect_loop'] = self._detect_redirect_loop(redirect_chain)
            else:
                data['redirect_chain'] = ''
                data['redirect_hops'] = 0
                data['final_destination'] = url
                data['has_redirect_chain'] = False
                data['redirect_loop'] = False
            
            # Adiciona informação de onde foi encontrada
            if url in self.url_source:
                source_url, anchor_text = self.url_source[url]
                data['found_on_url'] = source_url
                data['found_on_anchor_text'] = anchor_text
            else:
                data['found_on_url'] = ''
                data['found_on_anchor_text'] = ''
            
            self.crawled_data.append(data)
            
            # Se for HTML 200, extrai e adiciona links à fila
            if status_code == 200 and 'text/html' in response.headers.get('Content-Type', ''):
                self._process_links(response.text, url, depth)
            
            return True
            
        except requests.Timeout:
            logger.error(f"⏱️  Timeout: {url}")
            self._add_error_data(url, depth, 'Timeout')
            return False
        
        except requests.RequestException as e:
            logger.error(f"❌ Erro de requisição: {url} - {e}")
            self._add_error_data(url, depth, str(e))
            return False
        
        except Exception as e:
            logger.error(f"❌ Erro inesperado: {url} - {e}")
            self._add_error_data(url, depth, str(e))
            return False
    
    def _process_links(self, html: str, base_url: str, current_depth: int):
        """Processa links encontrados na página"""
        try:
            links = self.extractor.extract_links(html, base_url)
            
            for link_data in links:
                link_url = link_data['url']
                anchor_text = link_data['anchor_text']
                is_nofollow = link_data['is_nofollow']
                
                # Verifica nofollow
                if is_nofollow and not self.crawl_config.get('follow_nofollow', False):
                    continue
                
                # Adiciona à fila
                self._add_to_queue(
                    link_url,
                    depth=current_depth + 1,
                    source=base_url,
                    anchor=anchor_text
                )
        
        except Exception as e:
            logger.error(f"Erro ao processar links de {base_url}: {e}")
    
    def _add_to_queue(self, url: str, depth: int, source: str, anchor: str):
        """Adiciona URL à fila de crawl"""
        try:
            # Normaliza URL
            normalized_url = URLNormalizer.normalize(url)
            
            # Validações básicas
            if not URLNormalizer.is_valid(normalized_url):
                return
            
            # Já visitada?
            if normalized_url in self.visited:
                return
            
            # Verifica profundidade máxima
            max_depth = self.crawl_config.get('max_depth', 0)
            if max_depth > 0 and depth > max_depth:
                return
            
            # Verifica comprimento da URL
            max_length = self.config['safety']['max_url_length']
            if len(normalized_url) > max_length:
                logger.debug(f"URL muito longa ({len(normalized_url)} chars): {normalized_url}")
                return
            
            # Verifica se é interno
            if self.crawl_config.get('follow_internal_only', True):
                include_subdomains = self.crawl_config.get('follow_subdomains', False)
                if not URLNormalizer.is_same_domain(normalized_url, self.start_url, include_subdomains):
                    return
            
            # Verifica robots.txt
            if self.robots_checker and not self.robots_checker.can_fetch(normalized_url):
                logger.debug(f"Bloqueado por robots.txt: {normalized_url}")
                return
            
            # Verifica padrões de URL
            should_crawl, reason = self.pattern_matcher.should_crawl(normalized_url)
            if not should_crawl:
                logger.debug(f"Pulado ({reason}): {normalized_url}")
                self.stats['urls_skipped'] += 1
                return
            
            # Verifica limite de diretório
            if not self.directory_counter.add(normalized_url):
                logger.warning(f"Limite de diretório excedido: {normalized_url}")
                return
            
            # Adiciona à fila
            self.visited.add(normalized_url)
            self.to_crawl.append((normalized_url, depth))
            self.url_depth[normalized_url] = depth
            self.url_source[normalized_url] = (source, anchor)
            self.stats['total_urls'] += 1
            
        except Exception as e:
            logger.error(f"Erro ao adicionar URL à fila: {url} - {e}")
    
    def _should_continue_crawl(self) -> bool:
        """Verifica se deve continuar crawling"""
        max_urls = self.crawl_config.get('max_total_urls', 0)
        
        if max_urls > 0 and self.stats['urls_crawled'] >= max_urls:
            return False
        
        return True
    
    def _add_error_data(self, url: str, depth: int, error: str):
        """Adiciona dados de erro"""
        self.crawled_data.append({
            'url': url,
            'status_code': 0,
            'crawl_depth': depth,
            'error': error
        })
    
    def _follow_redirect_chain(self, start_url: str, first_response) -> tuple:
        """
        Segue uma cadeia de redirects até o destino final
        
        Args:
            start_url: URL inicial
            first_response: Primeira resposta (redirect)
        
        Returns:
            Tuple: (chain_list, final_url, final_status_code)
        """
        chain = [f"{start_url} ({first_response.status_code})"]
        current_url = start_url
        current_response = first_response
        
        max_redirects = self.config['safety'].get('max_redirect_chain', 5)
        redirects_followed = 0
        
        while current_response.status_code in [301, 302, 303, 307, 308]:
            redirects_followed += 1
            
            # Proteção contra loops infinitos
            if redirects_followed > max_redirects:
                logger.warning(f"Redirect chain excedeu limite ({max_redirects}): {start_url}")
                break
            
            # Pega Location header
            location = current_response.headers.get('Location', '')
            if not location:
                logger.warning(f"Redirect sem Location header: {current_url}")
                break
            
            # Resolve URL absoluta
            next_url = urljoin(current_url, location)
            
            # Verifica se já visitamos (loop)
            if next_url in [u.split(' ')[0] for u in chain]:
                chain.append(f"{next_url} (LOOP)")
                logger.warning(f"Redirect loop detectado: {' -> '.join(chain)}")
                return chain, next_url, current_response.status_code
            
            # Rate limiting
            self.rate_limiter.wait()
            
            # Faz próxima requisição
            try:
                current_response = self.session.get(
                    next_url,
                    timeout=self.config['rate_limiting']['request_timeout'],
                    allow_redirects=False
                )
                current_url = next_url
                chain.append(f"{current_url} ({current_response.status_code})")
                
            except Exception as e:
                logger.error(f"Erro ao seguir redirect de {current_url}: {e}")
                break
        
        return chain, current_url, current_response.status_code
    
    def _detect_redirect_loop(self, chain: list) -> bool:
        """Detecta se há loop na cadeia de redirects"""
        if not chain:
            return False
        
        # Extrai apenas as URLs (remove status codes)
        urls = [url.split(' ')[0] for url in chain]
        
        # Se há URLs duplicadas, é um loop
        return len(urls) != len(set(urls))
    
    def _finalize_crawl(self):
        """Finaliza crawl e gera relatórios"""
        self.stats['end_time'] = time.time()
        duration = self.stats['end_time'] - self.stats['start_time']
        
        # Calcula estatísticas
        self.stats['duration'] = format_duration(duration)
        self.stats['urls_per_second'] = self.stats['urls_crawled'] / duration if duration > 0 else 0
        
        if self.stats['response_times']:
            self.stats['avg_response_time'] = sum(self.stats['response_times']) / len(self.stats['response_times'])
        else:
            self.stats['avg_response_time'] = 0
        
        # Estatísticas de padrões
        self.stats['pattern_stats'] = self.pattern_matcher.get_statistics()
        
        # Imprime resumo
        self._print_summary()
        
        # Exporta dados
        self._export_data()
    
    def _print_summary(self):
        """Imprime resumo do crawl"""
        logger.info(f"\n{Fore.CYAN}{'='*80}")
        logger.info(f"{Fore.CYAN}📊 Resumo do Crawl")
        logger.info(f"{Fore.CYAN}{'='*80}\n")
        
        logger.info(f"⏱️  Duração: {Fore.GREEN}{self.stats['duration']}")
        logger.info(f"📄 Total de URLs: {Fore.GREEN}{self.stats['total_urls']}")
        logger.info(f"✅ URLs crawladas: {Fore.GREEN}{self.stats['urls_crawled']}")
        logger.info(f"⏭️  URLs puladas: {Fore.YELLOW}{self.stats['urls_skipped']}")
        logger.info(f"❌ URLs com erro: {Fore.RED}{self.stats['urls_failed']}")
        logger.info(f"⚡ Velocidade: {Fore.GREEN}{self.stats['urls_per_second']:.2f} URLs/segundo")
        logger.info(f"⏱️  Tempo médio de resposta: {Fore.GREEN}{self.stats['avg_response_time']:.3f}s")
        
        # Status codes
        logger.info(f"\n{Fore.CYAN}📌 Status Codes:")
        for code, count in sorted(self.stats['status_codes'].items()):
            logger.info(f"  {code}: {Fore.GREEN}{count}")
        
        # Estatísticas de padrões
        if self.stats['pattern_stats']:
            logger.info(f"\n{Fore.CYAN}🔍 Limites por Padrão de URL:")
            for description, pattern_stats in self.stats['pattern_stats'].items():
                count = pattern_stats['count']
                limit = pattern_stats['limit']
                percentage = pattern_stats['percentage']
                
                color = Fore.GREEN
                if percentage > 90:
                    color = Fore.RED
                elif percentage > 75:
                    color = Fore.YELLOW
                
                logger.info(
                    f"  {description}: {color}{count}/{limit} ({percentage:.1f}%)"
                )
    
    def _export_data(self):
        """Exporta dados coletados"""
        if not self.crawled_data:
            logger.warning("Nenhum dado para exportar")
            return
        
        logger.info(f"\n{Fore.CYAN}💾 Exportando dados...")
        
        exported_files = self.exporter.export(self.crawled_data, self.stats)
        
        if exported_files:
            logger.info(f"\n{Fore.GREEN}✅ Dados exportados com sucesso!")
            for filepath in exported_files:
                logger.info(f"  📁 {filepath}")
        else:
            logger.error("Erro ao exportar dados")


def main():
    """Função principal"""
    try:
        crawler = SEOCrawler('config.yaml')
        crawler.crawl()
    
    except FileNotFoundError:
        logger.error("Arquivo config.yaml não encontrado!")
    except Exception as e:
        logger.error(f"Erro fatal: {e}", exc_info=True)


if __name__ == '__main__':
    main()
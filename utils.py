"""
Utilidades para o SEO Crawler
Funções auxiliares para robots.txt, rate limiting, validação de URLs, etc.
"""

import time
import re
import logging
from urllib.parse import urlparse, urljoin, urlunparse
from urllib.robotparser import RobotFileParser
import random
from typing import Optional, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


class RateLimiter:
    """Controla a taxa de requisições para não sobrecarregar o servidor"""
    
    def __init__(self, requests_per_second: float, random_delay_range: Tuple[float, float] = None):
        self.requests_per_second = requests_per_second
        self.min_delay = 1.0 / requests_per_second if requests_per_second > 0 else 0
        self.random_delay_range = random_delay_range or (0, 0)
        self.last_request_time = 0
    
    def wait(self):
        """Aguarda o tempo necessário antes da próxima requisição"""
        if self.min_delay > 0:
            elapsed = time.time() - self.last_request_time
            sleep_time = self.min_delay - elapsed
            
            if sleep_time > 0:
                time.sleep(sleep_time)
            
            # Adiciona delay aleatório se configurado
            if self.random_delay_range[1] > 0:
                random_delay = random.uniform(*self.random_delay_range)
                time.sleep(random_delay)
        
        self.last_request_time = time.time()


class RobotsTxtChecker:
    """Verifica se uma URL pode ser rastreada conforme robots.txt"""
    
    def __init__(self, user_agent: str):
        self.user_agent = user_agent
        self.parsers = {}  # Cache de parsers por domínio
    
    def can_fetch(self, url: str) -> bool:
        """Verifica se a URL pode ser rastreada"""
        try:
            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            
            # Busca ou cria parser para este domínio
            if base_url not in self.parsers:
                parser = RobotFileParser()
                robots_url = urljoin(base_url, '/robots.txt')
                parser.set_url(robots_url)
                
                try:
                    parser.read()
                    self.parsers[base_url] = parser
                    logger.debug(f"Robots.txt carregado: {robots_url}")
                except Exception as e:
                    logger.warning(f"Erro ao ler robots.txt de {base_url}: {e}")
                    # Se não conseguir ler, permite por padrão
                    return True
            
            parser = self.parsers[base_url]
            can_fetch = parser.can_fetch(self.user_agent, url)
            
            if not can_fetch:
                logger.debug(f"URL bloqueada por robots.txt: {url}")
            
            return can_fetch
            
        except Exception as e:
            logger.error(f"Erro ao verificar robots.txt para {url}: {e}")
            return True  # Em caso de erro, permite por padrão


class URLPatternMatcher:
    """Gerencia limites e padrões de URLs"""
    
    def __init__(self, config: dict):
        self.pattern_limits = config.get('url_pattern_limits', [])
        self.exclude_patterns = config.get('exclude_patterns', [])
        self.include_patterns = config.get('include_patterns', [])
        
        # Contador de URLs por padrão
        self.pattern_counts = defaultdict(int)
        
        # Compila padrões regex
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compila padrões regex para melhor performance"""
        for pattern_config in self.pattern_limits:
            if pattern_config.get('regex', False):
                pattern_config['compiled'] = re.compile(pattern_config['pattern'])
        
        for pattern_config in self.exclude_patterns:
            if pattern_config.get('regex', False):
                pattern_config['compiled'] = re.compile(pattern_config['pattern'])
        
        for pattern_config in self.include_patterns:
            if pattern_config.get('regex', False):
                pattern_config['compiled'] = re.compile(pattern_config['pattern'])
    
    def should_crawl(self, url: str) -> Tuple[bool, Optional[str]]:
        """
        Verifica se a URL deve ser rastreada baseado nos padrões configurados
        
        Returns:
            Tuple[bool, Optional[str]]: (deve_rastrear, motivo_se_nao)
        """
        
        # Verifica exclusões primeiro
        for exclude_config in self.exclude_patterns:
            if self._matches_pattern(url, exclude_config):
                reason = exclude_config.get('description', 'padrão excluído')
                return False, f"Excluído: {reason}"
        
        # Se houver padrões de inclusão, verifica se URL corresponde
        if self.include_patterns:
            matched_include = False
            for include_config in self.include_patterns:
                if self._matches_pattern(url, include_config):
                    matched_include = True
                    break
            
            if not matched_include:
                return False, "Não corresponde aos padrões de inclusão"
        
        # Verifica limites por padrão
        for pattern_config in self.pattern_limits:
            if self._matches_pattern(url, pattern_config):
                pattern_id = pattern_config['pattern']
                limit = pattern_config.get('limit', 0)
                
                if limit > 0 and self.pattern_counts[pattern_id] >= limit:
                    description = pattern_config.get('description', pattern_id)
                    return False, f"Limite atingido para padrão: {description} ({limit} URLs)"
                
                # Incrementa contador
                self.pattern_counts[pattern_id] += 1
                logger.debug(f"URL corresponde ao padrão '{pattern_id}': {self.pattern_counts[pattern_id]}/{limit}")
        
        return True, None
    
    def _matches_pattern(self, url: str, pattern_config: dict) -> bool:
        """Verifica se URL corresponde a um padrão"""
        pattern = pattern_config['pattern']
        
        if pattern_config.get('regex', False):
            # Usa padrão compilado se disponível
            compiled = pattern_config.get('compiled')
            if compiled:
                return bool(compiled.search(url))
            else:
                return bool(re.search(pattern, url))
        else:
            # Busca simples de substring
            return pattern in url
    
    def get_statistics(self) -> dict:
        """Retorna estatísticas de URLs por padrão"""
        stats = {}
        for pattern_config in self.pattern_limits:
            pattern_id = pattern_config['pattern']
            description = pattern_config.get('description', pattern_id)
            limit = pattern_config.get('limit', 0)
            count = self.pattern_counts.get(pattern_id, 0)
            
            stats[description] = {
                'pattern': pattern_id,
                'count': count,
                'limit': limit,
                'percentage': (count / limit * 100) if limit > 0 else 0
            }
        
        return stats


class URLNormalizer:
    """Normaliza URLs para evitar duplicatas"""
    
    @staticmethod
    def normalize(url: str, remove_fragment: bool = True, sort_query: bool = True) -> str:
        """
        Normaliza uma URL para evitar duplicatas
        
        Args:
            url: URL a normalizar
            remove_fragment: Remove fragmento (#section)
            sort_query: Ordena parâmetros de query string
        
        Returns:
            URL normalizada
        """
        try:
            parsed = urlparse(url)
            
            # Remove fragmento se solicitado
            fragment = '' if remove_fragment else parsed.fragment
            
            # Ordena query string se solicitado
            query = parsed.query
            if sort_query and query:
                params = query.split('&')
                params.sort()
                query = '&'.join(params)
            
            # Reconstrói URL
            normalized = urlunparse((
                parsed.scheme,
                parsed.netloc.lower(),  # Domínio em minúscula
                parsed.path,
                parsed.params,
                query,
                fragment
            ))
            
            return normalized
            
        except Exception as e:
            logger.error(f"Erro ao normalizar URL {url}: {e}")
            return url
    
    @staticmethod
    def is_valid(url: str) -> bool:
        """Verifica se URL é válida"""
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except:
            return False
    
    @staticmethod
    def is_same_domain(url1: str, url2: str, include_subdomains: bool = False) -> bool:
        """Verifica se duas URLs são do mesmo domínio"""
        try:
            parsed1 = urlparse(url1)
            parsed2 = urlparse(url2)
            
            if include_subdomains:
                # Compara apenas domínio raiz
                domain1 = '.'.join(parsed1.netloc.split('.')[-2:])
                domain2 = '.'.join(parsed2.netloc.split('.')[-2:])
                return domain1 == domain2
            else:
                # Compara domínio completo
                return parsed1.netloc == parsed2.netloc
                
        except:
            return False
    
    @staticmethod
    def get_base_url(url: str) -> str:
        """Retorna URL base (scheme + netloc)"""
        try:
            parsed = urlparse(url)
            return f"{parsed.scheme}://{parsed.netloc}"
        except:
            return url


class DirectoryCounter:
    """Conta URLs por diretório para detectar loops infinitos"""
    
    def __init__(self, max_per_directory: int = 1000):
        self.max_per_directory = max_per_directory
        self.counts = defaultdict(int)
    
    def add(self, url: str) -> bool:
        """
        Adiciona URL e verifica se excedeu limite do diretório
        
        Returns:
            True se pode adicionar, False se excedeu limite
        """
        directory = self._get_directory(url)
        self.counts[directory] += 1
        
        if self.counts[directory] > self.max_per_directory:
            logger.warning(
                f"Limite de URLs excedido para diretório '{directory}': "
                f"{self.counts[directory]}/{self.max_per_directory}"
            )
            return False
        
        return True
    
    def _get_directory(self, url: str) -> str:
        """Extrai diretório da URL"""
        try:
            parsed = urlparse(url)
            path = parsed.path.rstrip('/')
            
            # Pega apenas o diretório, não o arquivo
            if '.' in path.split('/')[-1]:
                directory = '/'.join(path.split('/')[:-1])
            else:
                directory = path
            
            return f"{parsed.netloc}{directory}"
        except:
            return url


def format_duration(seconds: float) -> str:
    """Formata duração em formato legível"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def format_size(bytes: int) -> str:
    """Formata tamanho em bytes para formato legível"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024.0:
            return f"{bytes:.1f}{unit}"
        bytes /= 1024.0
    return f"{bytes:.1f}TB"

"""
Extrator de dados SEO
Extrai elementos HTML relevantes para análise de SEO
"""

import re
import json
import logging
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


class SEODataExtractor:
    """Extrai dados SEO de páginas HTML"""
    
    def __init__(self, config: dict):
        self.config = config.get('extraction', {})
    
    def extract(self, html: str, url: str, response_time: float = 0) -> Dict:
        """
        Extrai todos os dados SEO de uma página HTML
        
        Args:
            html: Conteúdo HTML da página
            url: URL da página
            response_time: Tempo de resposta em segundos
        
        Returns:
            Dicionário com todos os dados extraídos
        """
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            data = {
                'url': url,
                'response_time': round(response_time, 3)
            }
            
            # Extrai elementos básicos
            if self.config.get('extract_title', True):
                data.update(self._extract_title(soup))
            
            if self.config.get('extract_meta_description', True):
                data.update(self._extract_meta_description(soup))
            
            if self.config.get('extract_meta_keywords', False):
                data.update(self._extract_meta_keywords(soup))
            
            if self.config.get('extract_h1', True):
                data.update(self._extract_h1(soup))
            
            if self.config.get('extract_h2', True):
                data.update(self._extract_h2(soup))
            
            if self.config.get('extract_canonical', True):
                data.update(self._extract_canonical(soup, url))
            
            if self.config.get('extract_meta_robots', True):
                data.update(self._extract_meta_robots(soup))
            
            if self.config.get('extract_og_tags', True):
                data.update(self._extract_og_tags(soup))
            
            if self.config.get('extract_twitter_cards', False):
                data.update(self._extract_twitter_cards(soup))
            
            if self.config.get('extract_structured_data', True):
                data.update(self._extract_structured_data(soup))
            
            if self.config.get('extract_hreflang', True):
                data.update(self._extract_hreflang(soup))
            
            # Contagens
            if self.config.get('count_images', True):
                data.update(self._count_images(soup))
            
            if self.config.get('count_links_internal', True):
                data.update(self._count_links(soup, url))
            
            if self.config.get('count_words', True):
                data.update(self._count_words(soup))
            
            # Análises
            if self.config.get('detect_missing_alt_text', True):
                data.update(self._detect_missing_alt_text(soup))
            
            # Determina se é indexável
            data['indexable'] = self._is_indexable(data)
            
            # Tipo de conteúdo
            data['content_type'] = self._detect_content_type(url, soup)
            
            return data
            
        except Exception as e:
            logger.error(f"Erro ao extrair dados de {url}: {e}")
            return {'url': url, 'error': str(e)}
    
    def _extract_title(self, soup: BeautifulSoup) -> Dict:
        """Extrai title tag"""
        title_tag = soup.find('title')
        title = title_tag.get_text().strip() if title_tag else ''
        
        return {
            'title': title,
            'title_length': len(title)
        }
    
    def _extract_meta_description(self, soup: BeautifulSoup) -> Dict:
        """Extrai meta description"""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        description = meta_desc.get('content', '').strip() if meta_desc else ''
        
        return {
            'meta_description': description,
            'meta_description_length': len(description)
        }
    
    def _extract_meta_keywords(self, soup: BeautifulSoup) -> Dict:
        """Extrai meta keywords (obsoleto mas ainda usado)"""
        meta_kw = soup.find('meta', attrs={'name': 'keywords'})
        keywords = meta_kw.get('content', '').strip() if meta_kw else ''
        
        return {'meta_keywords': keywords}
    
    def _extract_h1(self, soup: BeautifulSoup) -> Dict:
        """Extrai H1 tags"""
        h1_tags = soup.find_all('h1')
        h1_texts = [h1.get_text().strip() for h1 in h1_tags if h1.get_text().strip()]
        
        return {
            'h1': h1_texts[0] if h1_texts else '',
            'h1_count': len(h1_texts),
            'h1_all': ' | '.join(h1_texts) if len(h1_texts) > 1 else ''
        }
    
    def _extract_h2(self, soup: BeautifulSoup) -> Dict:
        """Extrai H2 tags"""
        h2_tags = soup.find_all('h2')
        h2_count = len(h2_tags)
        
        return {
            'h2_count': h2_count,
            'h2_first': h2_tags[0].get_text().strip() if h2_tags else ''
        }
    
    def _extract_canonical(self, soup: BeautifulSoup, current_url: str) -> Dict:
        """Extrai canonical tag"""
        canonical_tag = soup.find('link', attrs={'rel': 'canonical'})
        canonical = ''
        
        if canonical_tag:
            canonical = canonical_tag.get('href', '').strip()
            # Resolve URL relativa
            if canonical and not canonical.startswith('http'):
                canonical = urljoin(current_url, canonical)
        
        return {
            'canonical': canonical,
            'self_canonical': canonical == current_url if canonical else False
        }
    
    def _extract_meta_robots(self, soup: BeautifulSoup) -> Dict:
        """Extrai meta robots"""
        meta_robots = soup.find('meta', attrs={'name': 'robots'})
        robots_content = meta_robots.get('content', '').lower() if meta_robots else ''
        
        # Verifica X-Robots-Tag (seria no header HTTP, não no HTML)
        # Aqui só pegamos do meta tag
        
        return {
            'meta_robots': robots_content,
            'robots_noindex': 'noindex' in robots_content,
            'robots_nofollow': 'robots_nofollow' in robots_content
        }
    
    def _extract_og_tags(self, soup: BeautifulSoup) -> Dict:
        """Extrai Open Graph tags"""
        og_tags = soup.find_all('meta', property=re.compile('^og:'))
        
        og_data = {}
        for tag in og_tags:
            property_name = tag.get('property', '').replace('og:', 'og_')
            content = tag.get('content', '').strip()
            og_data[property_name] = content
        
        return og_data
    
    def _extract_twitter_cards(self, soup: BeautifulSoup) -> Dict:
        """Extrai Twitter Card tags"""
        twitter_tags = soup.find_all('meta', attrs={'name': re.compile('^twitter:')})
        
        twitter_data = {}
        for tag in twitter_tags:
            name = tag.get('name', '').replace('twitter:', 'twitter_')
            content = tag.get('content', '').strip()
            twitter_data[name] = content
        
        return twitter_data
    
    def _extract_structured_data(self, soup: BeautifulSoup) -> Dict:
        """Extrai structured data (JSON-LD, Microdata)"""
        # JSON-LD
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        json_ld_count = len(json_ld_scripts)
        
        json_ld_types = []
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    json_ld_types.append(data.get('@type', 'Unknown'))
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            json_ld_types.append(item.get('@type', 'Unknown'))
            except:
                pass
        
        # Microdata (simplificado)
        microdata_items = soup.find_all(attrs={'itemtype': True})
        microdata_count = len(microdata_items)
        
        return {
            'structured_data_jsonld_count': json_ld_count,
            'structured_data_jsonld_types': ', '.join(json_ld_types) if json_ld_types else '',
            'structured_data_microdata_count': microdata_count
        }
    
    def _extract_hreflang(self, soup: BeautifulSoup) -> Dict:
        """Extrai hreflang tags"""
        hreflang_tags = soup.find_all('link', rel='alternate', hreflang=True)
        hreflang_count = len(hreflang_tags)
        
        hreflang_langs = [tag.get('hreflang') for tag in hreflang_tags]
        
        return {
            'hreflang_count': hreflang_count,
            'hreflang_languages': ', '.join(hreflang_langs) if hreflang_langs else ''
        }
    
    def _count_images(self, soup: BeautifulSoup) -> Dict:
        """Conta imagens"""
        images = soup.find_all('img')
        
        return {
            'images_count': len(images)
        }
    
    def _count_links(self, soup: BeautifulSoup, current_url: str) -> Dict:
        """Conta links internos e externos"""
        links = soup.find_all('a', href=True)
        
        internal_count = 0
        external_count = 0
        nofollow_count = 0
        
        current_domain = urlparse(current_url).netloc
        
        for link in links:
            href = link.get('href', '').strip()
            
            # Ignora âncoras e javascript
            if not href or href.startswith('#') or href.startswith('javascript:'):
                continue
            
            # Resolve URL absoluta
            absolute_url = urljoin(current_url, href)
            link_domain = urlparse(absolute_url).netloc
            
            # Conta interno vs externo
            if link_domain == current_domain:
                internal_count += 1
            else:
                external_count += 1
            
            # Conta nofollow
            rel = link.get('rel', [])
            if isinstance(rel, list):
                rel = ' '.join(rel)
            if 'nofollow' in rel.lower():
                nofollow_count += 1
        
        return {
            'internal_links_count': internal_count,
            'external_links_count': external_count,
            'nofollow_links_count': nofollow_count
        }
    
    def _count_words(self, soup: BeautifulSoup) -> Dict:
        """Conta palavras no conteúdo"""
        # Remove scripts e styles
        for script in soup(['script', 'style', 'nav', 'footer', 'header']):
            script.decompose()
        
        text = soup.get_text()
        words = re.findall(r'\w+', text)
        
        return {
            'word_count': len(words)
        }
    
    def _detect_missing_alt_text(self, soup: BeautifulSoup) -> Dict:
        """Detecta imagens sem alt text"""
        images = soup.find_all('img')
        images_without_alt = 0
        
        for img in images:
            if not img.get('alt'):
                images_without_alt += 1
        
        return {
            'images_without_alt': images_without_alt
        }
    
    def _is_indexable(self, data: Dict) -> bool:
        """Determina se página é indexável"""
        # Não é indexável se tiver noindex
        if data.get('robots_noindex', False):
            return False
        
        # Não é indexável se canonical apontar para outra URL
        canonical = data.get('canonical', '')
        url = data.get('url', '')
        
        if canonical and canonical != url:
            return False
        
        return True
    
    def _detect_content_type(self, url: str, soup: BeautifulSoup) -> str:
        """Detecta tipo de conteúdo da página"""
        # Verifica pela URL primeiro
        if '/produto/' in url or '/p/' in url:
            return 'product'
        elif '/categoria/' in url or '/c/' in url:
            return 'category'
        elif '/busca/' in url or '/search' in url:
            return 'search'
        elif '/blog/' in url:
            return 'blog'
        
        # Verifica por structured data
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    schema_type = data.get('@type', '')
                    if schema_type == 'Product':
                        return 'product'
                    elif schema_type in ['CollectionPage', 'ItemList']:
                        return 'category'
                    elif schema_type in ['Article', 'BlogPosting']:
                        return 'blog'
            except:
                pass
        
        # Default
        parsed = urlparse(url)
        if parsed.path == '/' or parsed.path == '':
            return 'homepage'
        
        return 'page'
    
    def extract_links(self, html: str, base_url: str) -> List[Dict]:
        """
        Extrai todos os links de uma página
        
        Args:
            html: Conteúdo HTML
            base_url: URL base para resolver links relativos
        
        Returns:
            Lista de dicionários com informações dos links
        """
        try:
            soup = BeautifulSoup(html, 'lxml')
            links = []
            
            for link_tag in soup.find_all('a', href=True):
                href = link_tag.get('href', '').strip()
                
                # Ignora âncoras vazias e javascript
                if not href or href.startswith('javascript:'):
                    continue
                
                # Resolve URL absoluta
                absolute_url = urljoin(base_url, href)
                
                # Pega anchor text
                anchor_text = link_tag.get_text().strip()
                
                # Verifica nofollow
                rel = link_tag.get('rel', [])
                if isinstance(rel, list):
                    rel = ' '.join(rel)
                is_nofollow = 'nofollow' in rel.lower()
                
                links.append({
                    'url': absolute_url,
                    'anchor_text': anchor_text,
                    'is_nofollow': is_nofollow
                })
            
            return links
            
        except Exception as e:
            logger.error(f"Erro ao extrair links de {base_url}: {e}")
            return []

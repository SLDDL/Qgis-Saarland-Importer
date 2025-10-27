#!/usr/bin/env python3
"""
Saarland Geoportal Link Finder
Finds WMS/WFS/WCS/WMTS links from the Saarland geoportal with their categories
"""

import os
import sys
import re
import json
import time
from typing import List, Dict
import logging
from urllib.parse import urljoin

# Add the vendor directory to sys.path to use bundled dependencies
current_dir = os.path.dirname(os.path.abspath(__file__))
vendor_dir = os.path.join(os.path.dirname(current_dir), 'vendor')
if vendor_dir not in sys.path:
    sys.path.insert(0, vendor_dir)

# Now import the dependencies from vendor directory
import requests
from bs4 import BeautifulSoup

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SaarlandGeoLinkFinder:
    def __init__(self):
        logger.info("Initializing SaarlandGeoLinkFinder...")
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.found_links = []
        self.visited_urls = set()
        logger.info("SaarlandGeoLinkFinder initialized successfully")
        
        # Service types we're looking for
        self.service_patterns = [
            r'wms',
            r'wfs', 
            r'wcs',
            r'wmts'
        ]
        
        # URL patterns that indicate geo services
        self.geo_url_patterns = [
            r'service=wms',
            r'service=wfs',
            r'service=wcs', 
            r'service=wmts',
            r'/wms\?',
            r'/wfs\?',
            r'/wcs\?',
            r'/wmts\?',
            r'\.wms',
            r'\.wfs',
            r'\.wcs',
            r'\.wmts'
        ]

    def get_page_content(self, url: str) -> BeautifulSoup:
        """Fetch and parse a web page"""
        try:
            logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def is_geo_service_link(self, url: str) -> str:
        """Check if URL is a geo service and return service type"""
        url_lower = url.lower()
        for pattern in self.geo_url_patterns:
            if re.search(pattern, url_lower):
                # Extract service type
                for service in self.service_patterns:
                    if service in url_lower:
                        return service.upper()
                # If no specific service found in URL, try to determine from pattern
                if 'wms' in pattern:
                    return 'WMS'
                elif 'wfs' in pattern:
                    return 'WFS'
                elif 'wcs' in pattern:
                    return 'WCS'
                elif 'wmts' in pattern:
                    return 'WMTS'
        return None

    def extract_category_hierarchy(self, element) -> List[str]:
        """Extract category hierarchy from the HTML structure"""
        categories = []
        
        # Look for the section/container that holds this link
        current = element
        max_depth = 10
        depth = 0
        
        # First, try to find the immediate parent containers
        while current and depth < max_depth:
            depth += 1
            current = current.parent
            if not current or current.name in ['html', 'body', 'document']:
                break
                
            # Look for section containers, divs with specific classes, or table structures
            current_text = current.get_text(strip=True) if current else ""
            
            # Skip if text is too long (likely containing multiple items)
            if len(current_text) > 200:
                continue
                
            # Look for headings within this container or preceding it
            headings_found = []
            
            # Check for headings within the current container
            for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                headings = current.find_all(tag)
                for heading in headings:
                    h_text = heading.get_text(strip=True)
                    if h_text and len(h_text) < 100 and h_text not in headings_found:
                        headings_found.append(h_text)
            
            # Also look for preceding headings
            for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                heading = current.find_previous(tag)
                if heading:
                    h_text = heading.get_text(strip=True)
                    if h_text and len(h_text) < 100 and h_text not in headings_found:
                        # Check if this heading is reasonably close to our element
                        # by seeing if it's within a reasonable distance
                        try:
                            heading_parent = heading.parent
                            if heading_parent and (current in heading_parent.descendants or 
                                                 heading_parent in current.parents):
                                headings_found.insert(0, h_text)
                        except Exception:
                            pass
        
        # Now work backwards from the element to find the proper hierarchy
        current = element
        depth = 0
        
        while current and depth < max_depth:
            depth += 1
            
            # Look for table rows or divs that might contain category info
            if current.name in ['tr', 'div', 'section', 'article']:
                # Check for heading elements in this container or before it
                for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    # Look for headings that precede this element
                    heading = current.find_previous(tag)
                    if heading:
                        h_text = heading.get_text(strip=True)
                        # Clean up the heading text
                        h_text = re.sub(r'\s+', ' ', h_text).strip()
                        
                        # Skip if it's too long or already captured
                        if (h_text and len(h_text) < 100 and len(h_text) > 2 and 
                            h_text not in categories and
                            not any(existing in h_text for existing in categories)):
                            categories.insert(0, h_text)
                            break
            
            current = current.parent
            if not current or current.name in ['html', 'body']:
                break
        
        # Post-process categories to fix common patterns
        cleaned_categories = []
        for cat in categories:
            # Remove extra whitespace and common noise
            cat = re.sub(r'\s+', ' ', cat).strip()
            cat = re.sub(r'^[\d\.\-\s]+', '', cat)  # Remove leading numbers/dots
            cat = re.sub(r'\s*\([^)]*\)\s*$', '', cat)  # Remove trailing parentheses info in some cases
            
            if (cat and len(cat) > 2 and cat not in cleaned_categories and
                not cat.lower().startswith('http') and
                not re.match(r'^(download|darstellung|capabilities)', cat.lower())):
                cleaned_categories.append(cat)
        
        # If we have categories, ensure we have the proper hierarchy
        # Add known main categories if missing
        if cleaned_categories:
            # Check if we need to add "Geobasisdaten (opendata)" as root
            if not any('geobasisdaten' in cat.lower() for cat in cleaned_categories):
                cleaned_categories.insert(0, "Geobasisdaten (opendata)")
            
            # For ALKIS-related services, ensure proper hierarchy
            alkis_keywords = ['alkis', 'hausumringe', 'hauskoordinaten', 'bodenschätzung']
            if any(keyword in ' '.join(cleaned_categories).lower() for keyword in alkis_keywords):
                # If we have ALKIS-related content but no explicit "ALKIS" category
                if not any('alkis' == cat.lower() for cat in cleaned_categories):
                    # Find where to insert ALKIS category
                    geobasisdaten_idx = -1
                    for i, cat in enumerate(cleaned_categories):
                        if 'geobasisdaten' in cat.lower():
                            geobasisdaten_idx = i
                            break
                    if geobasisdaten_idx >= 0:
                        cleaned_categories.insert(geobasisdaten_idx + 1, "ALKIS")
        
        return cleaned_categories

    def find_links_in_page(self, url: str, soup: BeautifulSoup) -> List[Dict]:
        """Find all geo service links in a page with their categories"""
        links_found = []
        
        # Find all links in the page
        all_links = soup.find_all('a', href=True)
        
        for link in all_links:
            href = link['href']
            absolute_url = urljoin(url, href)
            
            # Check if this is a geo service link
            service_type = self.is_geo_service_link(absolute_url)
            if service_type:
                # Extract categories using improved method
                categories = self.extract_category_hierarchy_improved(link, soup, url)
                
                # Get link text
                link_text = link.get_text(strip=True)
                
                link_info = {
                    'url': absolute_url,
                    'service_type': service_type,
                    'categories': categories,
                    'link_text': link_text,
                    'source_page': url
                }
                
                links_found.append(link_info)
                logger.info(f"Found {service_type} link: {absolute_url}")
                logger.info(f"Categories: {' -> '.join(categories)}")
        
        return links_found

    def extract_category_hierarchy_improved(self, element, soup: BeautifulSoup, source_url: str = "") -> List[str]:
        """Improved category extraction based on Saarland geoportal structure"""
        
        # Determine if this is from historical page
        is_historical = 'historische_geobasisdatenuebersicht' in source_url
        
        # Manual mapping based on content
        categories = []
        
        if is_historical:
            categories.append("Historische Geobasisdaten (opendata)")
        else:
            categories.append("Geobasisdaten (opendata)")
        
        # Find the accordion structure - look for the immediate parent accordion item
        current = element
        found_main_category = None
        found_subcategory = None
        
        # Look up the DOM tree to find the specific accordion item containing this link
        for _ in range(20):  # Look deeper in the DOM
            if current:
                current = current.parent
                if not current:
                    break
                
                # Check if this is an accordion item
                if current.get('class') and 'accordion-item' in current.get('class', []):
                    # Found an accordion item, look for its header
                    header = current.find('h2', class_='accordion-header')
                    if header:
                        button = header.find('button', class_='accordion-button')
                        if button:
                            subcategory_text = button.get_text(strip=True)
                            if subcategory_text and not found_subcategory:
                                found_subcategory = subcategory_text
                
                # Check for main category card headers (like "ALKIS")
                if current.get('class') and 'card-header' in current.get('class', []):
                    h3 = current.find('h3')
                    if h3:
                        button = h3.find('button')
                        if button:
                            main_category_text = button.get_text(strip=True)
                            if main_category_text and not found_main_category:
                                found_main_category = main_category_text
                
                # Also check for accordion cards with id like "accordionGroup1" 
                if current.get('id') and 'accordionGroup' in current.get('id', ''):
                    # We're in a main category group, look for the parent card header
                    parent = current.parent
                    if parent:
                        card_header = parent.find_previous('div', class_='card-header')
                        if card_header and not found_main_category:
                            h3 = card_header.find('h3')
                            if h3:
                                button = h3.find('button')
                                if button:
                                    main_category_text = button.get_text(strip=True)
                                    if main_category_text:
                                        found_main_category = main_category_text
        
        # Use found categories or fallback
        if found_main_category:
            categories.append(found_main_category)
        else:
            # Fallback to keyword detection
            context_text = ""
            parent_row = element.find_parent('tr')
            if parent_row:
                context_text = parent_row.get_text().lower()
            
            if any(keyword in context_text for keyword in ['alkis', 'liegenschafts', 'kataster']):
                categories.append("ALKIS")
            elif any(keyword in context_text for keyword in ['inspire', 'verwaltung']):
                categories.append("Inspire")
            else:
                categories.append("General")
        
        if found_subcategory:
            categories.append(found_subcategory)
        else:
            # Fallback subcategory detection
            context_text = ""
            parent_row = element.find_parent('tr')
            if parent_row:
                context_text = parent_row.get_text().lower()
            
            if 'hausumringe' in context_text:
                categories.append("Hausumringe")
            elif 'hauskoordinaten' in context_text:
                categories.append("Hauskoordinaten")
            elif 'bodenschätzung' in context_text:
                categories.append("ALKIS Bodenschätzung")
            elif 'vereinfacht' in context_text:
                categories.append("WFS SL ALKIS Vereinfacht")
            elif 'saarland sw' in context_text:
                if 'gid6' in context_text:
                    categories.append("ALKIS Saarland SW GID6")
                else:
                    categories.append("ALKIS Saarland SW")
            else:
                categories.append("General Services")
        
        # Ensure we always have exactly 3 levels
        while len(categories) < 3:
            categories.append("Services")
        
        return categories[:3]  # Return exactly 3 levels

    def should_follow_link(self, url: str) -> bool:
        """Determine if we should follow a link for recursive searching"""
        # Only follow the specific historical data page as mentioned
        if 'historische_geobasisdatenuebersicht' in url:
            return True
        
        # Don't follow external links
        if not url.startswith('https://geoportal.saarland.de'):
            return False
            
        # Don't follow if already visited
        if url in self.visited_urls:
            return False
            
        return False  # For now, only follow the specific page mentioned

    def crawl_page(self, url: str, max_depth: int = 2, current_depth: int = 0):
        """Crawl a page and optionally follow links"""
        logger.info(f"Crawling page: {url} (depth: {current_depth}, max_depth: {max_depth})")
        
        if url in self.visited_urls or current_depth > max_depth:
            logger.info(f"Skipping {url} - already visited or max depth reached")
            return
            
        self.visited_urls.add(url)
        
        soup = self.get_page_content(url)
        if not soup:
            logger.warning(f"Failed to get page content for: {url}")
            return
            
        # Find links in current page
        logger.info(f"Looking for geo service links on page: {url}")
        page_links = self.find_links_in_page(url, soup)
        logger.info(f"Found {len(page_links)} geo service links on this page")
        self.found_links.extend(page_links)
        
        # Follow specific links if depth allows
        if current_depth < max_depth:
            all_links = soup.find_all('a', href=True)
            logger.info(f"Found {len(all_links)} total links to check for following")
            for link in all_links:
                href = link['href']
                absolute_url = urljoin(url, href)
                
                if self.should_follow_link(absolute_url):
                    logger.info(f"Following link: {absolute_url}")
                    time.sleep(1)  # Be polite to the server
                    self.crawl_page(absolute_url, max_depth, current_depth + 1)

    def save_results(self, filename: str = 'saarland_geo_links.json'):
        """Save results to JSON file grouped by nested categories (Geobasis/history -> category -> subcategory -> links)"""
        logger.info(f"Saving {len(self.found_links)} results to {filename}...")
        
        def insert_nested(d, categories, link_info):
            if not categories:
                if 'links' not in d:
                    d['links'] = []
                d['links'].append(link_info)
                return
            cat = categories[0]
            if cat not in d:
                d[cat] = {}
            insert_nested(d[cat], categories[1:], link_info)

        nested = {}
        for link in self.found_links:
            # Remove empty or duplicate categories
            categories = [c for i, c in enumerate(link['categories']) if c and (i == 0 or c != link['categories'][i-1])]
            link_info = {
                'url': link['url'],
                'service_type': link['service_type'],
                'link_text': link['link_text'],
                'source_page': link['source_page']
            }
            insert_nested(nested, categories, link_info)

        # Service type summary
        service_types = {}
        for link in self.found_links:
            st = link['service_type']
            service_types[st] = service_types.get(st, 0) + 1

        # Count categories (leaf nodes with links)
        def count_leaf_categories(d):
            count = 0
            for v in d.values():
                if isinstance(v, dict):
                    count += count_leaf_categories(v)
                elif isinstance(v, list):
                    count += 1
            return count

        final_structure = {
            'summary': {
                'total_links': len(self.found_links),
                'total_categories': count_leaf_categories(nested),
                'service_types': service_types
            },
            'categories': nested
        }

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(final_structure, f, indent=2, ensure_ascii=False)
            logger.info(f"Successfully saved {len(self.found_links)} links to {filename}")
            logger.info(f"Service types found: {service_types}")
        except Exception as e:
            logger.error(f"Failed to save results to {filename}: {e}")

    def print_results(self):
        """Print results in a formatted way grouped by categories"""
        print("\n" + "="*80)
        print("SAARLAND GEOPORTAL GEO SERVICE LINKS")
        print("="*80)
        
        # Group by category hierarchy for better display
        grouped_results = {}
        for link in self.found_links:
            category_path = " -> ".join(link['categories'])
            if category_path not in grouped_results:
                grouped_results[category_path] = []
            grouped_results[category_path].append(link)
        
        # Print summary
        print("\nSUMMARY:")
        print(f"Total links found: {len(self.found_links)}")
        print(f"Total categories: {len(grouped_results)}")
        
        # Service type summary
        service_counts = {}
        for link in self.found_links:
            service_type = link['service_type']
            service_counts[service_type] = service_counts.get(service_type, 0) + 1
        
        print("Service types:")
        for service_type, count in service_counts.items():
            print(f"  {service_type}: {count}")
        
        # Print by category
        print("\nSERVICES BY CATEGORY:")
        print("-" * 80)
        
        for category_path, links in grouped_results.items():
            print(f"\n📁 {category_path} ({len(links)} services)")
            print("-" * 50)
            
            for i, link in enumerate(links, 1):
                print(f"\n{i}. {link['link_text']} ({link['service_type']})")
                print(f"   URL: {link['url']}")
                print(f"   Source: {link['source_page']}")

def main():
    finder = SaarlandGeoLinkFinder()
    
    # Main URL to crawl
    main_url = "https://geoportal.saarland.de/app-article/geobasisdatenuebersicht/"
    
    logger.info("Starting Saarland Geoportal link finder...")
    logger.info(f"Main URL: {main_url}")
    
    try:
        # Crawl the main page and allowed sub-pages
        finder.crawl_page(main_url, max_depth=1)
        
        # Print and save results
        finder.print_results()
        finder.save_results()
        
        print(f"\nTotal links found: {len(finder.found_links)}")
        print("Results saved to 'saarland_geo_links.json'")
        
    except KeyboardInterrupt:
        logger.info("Crawling interrupted by user")
        finder.print_results()
        finder.save_results()
    except Exception as e:
        logger.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
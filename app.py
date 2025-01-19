from langchain_groq import ChatGroq as Groq
from langchain_google_community import GoogleSearchAPIWrapper
import requests
import warnings
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import re
import time
import json
from urllib.parse import urljoin, urlparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from sklearn.preprocessing import MinMaxScaler
import numpy as np

class WebScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def is_blog_url(self, url: str) -> bool:
        blog_indicators = [
            '/blog/', 'medium.com', 'wordpress.com', 'blogspot.com',
            'substack.com', '/posts/', '/article/', '/insights/'
        ]
        return any(indicator in url.lower() for indicator in blog_indicators)

    def extract_main_content(self, soup: BeautifulSoup) -> str:
        for script in soup(['script', 'style', 'nav', 'header', 'footer']):
            script.decompose()
            
        content_containers = soup.find_all(['article', 'main', 'div'], class_=re.compile(
            r'(content|post|article|blog|entry)', re.I))
            
        if not content_containers:
            content_containers = [soup.find('body')]
            
        text_content = []
        for container in content_containers:
            if container:
                paragraphs = container.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                text_content.extend([p.text.strip() for p in paragraphs if p.text.strip()])
                
        return ' '.join(text_content)

    def scrape_url(self, url: str) -> Dict:
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.title.string if soup.title else "No title found"
            content = self.extract_main_content(soup)
            
            return {
                'url': url,
                'title': title.strip(),
                'content': content[:2000] + "..." if len(content) > 2000 else content
            }
        except Exception as e:
            return {
                'url': url,
                'title': "Error scraping content",
                'content': f"Error: {str(e)}"
            }

    def extract_reddit_content(self, url: str) -> Dict:
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.find('h1').text.strip() if soup.find('h1') else "Title not found"
            content = soup.find('div', {'data-test-id': 'post-content'}).text.strip() if soup.find('div', {'data-test-id': 'post-content'}) else "Content not found"
            
            return {
                'url': url,
                'title': title,
                'content': content
            }
        except Exception as e:
            return {
                'url': url,
                'title': "Error fetching post",
                'content': f"Error: {str(e)}"
            }

    def extract_quora_content(self, url: str) -> Dict:
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.find('span', {'class': 'q-box qu-userSelect--text'}).text.strip() if soup.find('span', {'class': 'q-box qu-userSelect--text'}) else "Question not found"
            answers = [answer.text.strip() for answer in soup.find_all('div', {'class': 'q-text qu-wordBreak--break-word'})]
            content = "\n\n".join(answers[:3])
            
            return {
                'url': url,
                'title': title,
                'content': content
            }
        except Exception as e:
            return {
                'url': url,
                'title': "Error fetching Quora post",
                'content': f"Error: {str(e)}"
            }

class ResearchAnalyzer:
    def __init__(self, groq_api_key: str, google_api_key: str, google_cse_id: str):
        self.llm = Groq(
            api_key=groq_api_key,
            model_name="llama-3.1-8b-instant",
            temperature=0.3
        )
        
        self.google_search = GoogleSearchAPIWrapper(
            google_api_key=google_api_key,
            google_cse_id=google_cse_id
        )
        
        self.web_scraper = WebScraper()
        
        self.question_prompt = """
        Generate specific search queries based on the research details:
        
        Domain: {domain}
        Project: {project}
        Research Description: {description}
        
        Generate 20 search queries:
        - 5 general web queries
        - 5 Reddit-specific queries
        - 5 Quora-specific queries
        - 5 blog/article-specific queries
        
        Format as a Python dictionary:
        {{
            'general': [...],
            'reddit': [...],
            'quora': [...],
            'blog': [...]
        }}
        """

        self.analysis_prompt = """
        Provide a comprehensive analysis based on the collected data:
        
        Domain: {domain}
        Project: {project}
        Research Description: {description}
        
        Data:
        {data}
        
        Include:
        1. Synthesized insights
        2. Key patterns and trends
        3. Differences between source types
        4. Actionable conclusions
        5. Next steps or deeper investigation areas
        """

        self.langflow_settings = {
            "BASE_API_URL": "https://api.langflow.astra.datastax.com",
            "LANGFLOW_ID": "5213d7fa-9299-49d0-8a8e-df3f381ee281",
            "FLOW_ID": "2fe3fea5-3d65-4c82-b9ad-a0928f5598f3",
            "APPLICATION_TOKEN": "AstraCS:TnPwYfUZNRUHWyZvYlHDQwIj:f9670050a47e20efe713939e8e84c5e52565f37317af88e6321d8e4e020188c2",
            "TWEAKS": {
                # Tweak settings as needed
            }
        }

    def search_google(self, query: str) -> List[Dict]:
        try:
            results = self.google_search.results(query, num_results=3)
            return [{
                'title': result.get('title', ''),
                'link': result.get('link', ''),
                'snippet': result.get('snippet', '')
            } for result in results]
        except Exception as e:
            print(f"Error in Google search: {e}")
            return []

    def generate_questions(self, domain: str, project: str, description: str) -> Dict[str, List[str]]:
        prompt = self.question_prompt.format(
            domain=domain,
            project=project,
            description=description
        )
        response = self.llm.predict(prompt)
        
        try:
            questions = eval(response)
            if not isinstance(questions, dict) or not all(len(v) == 5 for v in questions.values()):
                raise ValueError
            return questions
        except:
            questions = {
                'general': [],
                'reddit': [],
                'quora': [],
                'blog': []
            }
            current_category = None
            
            for line in response.split('\n'):
                line = line.strip()
                if any(category in line.lower() for category in questions.keys()):
                    current_category = next(cat for cat in questions.keys() if cat in line.lower())
                elif line and current_category and len(questions[current_category]) < 5:
                    questions[current_category].append(line.strip('- "\''))
            
            for category in questions:
                while len(questions[category]) < 5:
                    questions[category].append(f"Default {category} query about {project}")
                    
            return questions

    def search_and_collect(self, questions: Dict[str, List[str]]) -> Dict[str, List[Dict]]:
        search_results = {
            'general': [],
            'reddit': [],
            'quora': [],
            'blogs': []
        }
        
        # Collect all URLs for each category
        general_urls = []
        for query in questions['general']:
            general_urls.extend([result['link'] for result in self.search_google(query)])
            time.sleep(1)
        
        reddit_urls = []
        for query in questions['reddit']:
            results = self.search_google(f"{query} site:reddit.com")
            reddit_urls.extend([result['link'] for result in results if 'reddit.com' in result['link'] and '/comments/' in result['link']])
            time.sleep(1)
        
        quora_urls = []
        for query in questions['quora']:
            results = self.search_google(f"{query} site:quora.com")
            quora_urls.extend([result['link'] for result in results if 'quora.com' in result['link'] and '/answer/' in result['link']])
            time.sleep(1)
        
        blog_urls = []
        for query in questions['blog']:
            results = self.search_google(f"{query} blog OR article")
            blog_urls.extend([result['link'] for result in results if self.web_scraper.is_blog_url(result['link'])])
            time.sleep(1)
        
        # Set number of worker threads
        NUM_WORKERS = 500
        
        # Scrape general URLs
        with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
            general_futures = [executor.submit(self.web_scraper.scrape_url, url) for url in general_urls]
            for future in as_completed(general_futures):
                result = future.result()
                search_results['general'].append(result)
        
        # Scrape Reddit URLs
        with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
            reddit_futures = [executor.submit(self.web_scraper.extract_reddit_content, url) for url in reddit_urls]
            for future in as_completed(reddit_futures):
                result = future.result()
                search_results['reddit'].append(result)
        
        # Scrape Quora URLs
        with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
            quora_futures = [executor.submit(self.web_scraper.extract_quora_content, url) for url in quora_urls]
            for future in as_completed(quora_futures):
                result = future.result()
                search_results['quora'].append(result)
        
        # Scrape blog URLs
        with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
            blog_futures = [executor.submit(self.web_scraper.scrape_url, url) for url in blog_urls]
            for future in as_completed(blog_futures):
                result = future.result()
                search_results['blogs'].append(result)
        
        return search_results

    def format_results(self, search_results: Dict[str, List[Dict]]) -> tuple[str, Dict[str, List[str]]]:
        formatted_text = []
        sources = {
            'general': [],
            'reddit': [],
            'quora': [],
            'blogs': []
        }
        
        for category in ['general', 'reddit', 'quora', 'blogs']:
            formatted_text.append(f"\n{category.title()} Results:")
            for result in search_results[category]:
                formatted_text.append(f"- Title: {result.get('title', 'No title')}")
                url = result.get('link', result.get('url', 'No URL'))
                formatted_text.append(f"  URL: {url}")
                content = result.get('snippet', result.get('content', 'No content'))
                formatted_text.append(f"  Content: {content}\n")
                sources[category].append(url)
        
        return "\n".join(formatted_text), sources

    def extract_resource_links(self, search_results: Dict[str, List[Dict]]) -> List[str]:
        links = []
        for category in search_results:
            for result in search_results[category]:
                url = result.get('link', result.get('url', ''))
                if url:
                    links.append(url)
        return links

    def parse_triggers_competitors(self, response: str) -> Tuple[List[Dict[str, int]], List[str]]:
        """
        Parse the effective triggers with weightage and competitors from the AI's response.
        """
        triggers_match = re.search(r'Effective Triggers: \[(.*?)\]', response)
        triggers = []
        if triggers_match:
            triggers = [{"trigger": trigger.strip(' "\''), "weightage": int(weightage.strip())} 
                        for trigger, weightage in re.findall(r'(\w+)\s*\((\d+)\)', triggers_match.group(1))]
        
        competitors_match = re.search(r'Competitors: \[(.*?)\]', response)
        competitors = []
        if competitors_match:
            competitors = [competitor.strip(' "\'') for competitor in competitors_match.group(1).split(',')]
        
        return triggers, competitors

    def parse_word_cloud(self, response: str) -> List[str]:
        """
        Parse the word cloud data and return a list of words.
        """
        match = re.search(r'Word Cloud Data: \[(.*?)\]', response)
        if match:
            words = [word.strip(' "\'') for word in match.group(1).split(',')]
            return words
        else:
            return []

    def parse_pain_points(self, response: str) -> List[str]:
        """
        Parse the pain points from the AI's response.
        """
        match = re.search(r'Pain Points: \[(.*?)\]', response)
        if match:
            pain_points = [point.strip(' "\'') for point in match.group(1).split(',')]
            return pain_points
        else:
            return []

    def process_full_analysis_with_datastax(self, initial_analysis: str) -> Optional[str]:
        """
        Send the initial analysis to DataStax for refinement.
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.langflow_settings['APPLICATION_TOKEN']}",
                "Content-Type": "application/json"
            }
            payload = {
                "langflow_id": self.langflow_settings["LANGFLOW_ID"],
                "flow_id": self.langflow_settings["FLOW_ID"],
                "input": initial_analysis,
                "tweaks": self.langflow_settings["TWEAKS"]
            }
            response = requests.post(
                f"{self.langflow_settings['BASE_API_URL']}/process",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            refined_analysis = response.json().get("output", "")
            return refined_analysis
        except Exception as e:
            print(f"Error processing analysis with DataStax: {e}")
            return None

    def analyze(self, domain: str, project: str, description: str) -> Dict:
        try:
            # Generate questions and collect data
            questions = self.generate_questions(domain, project, description)
            search_results = self.search_and_collect(questions)
            formatted_data, sources = self.format_results(search_results)
            
            # Extract resource links
            resource_links = self.extract_resource_links(search_results)
            
            # Generate initial analysis
            analysis_prompt = self.analysis_prompt.format(
                domain=domain,
                project=project,
                description=description,
                data=formatted_data
            )
            initial_analysis = self.llm.predict(analysis_prompt)
            
            # Process initial analysis with DataStax
            refined_analysis = self.process_full_analysis_with_datastax(initial_analysis)
            if refined_analysis is None:
                refined_analysis = initial_analysis  # Fallback to initial analysis if DataStax fails
            
            # Prompt for effective triggers and competitors
            triggers_competitors_prompt = f"""
            Given the domain, project, and description, extract the top 5 effective triggers with weightage (0-100) and top 5 competitors as lists.

            Format your response exactly as follows:
            Effective Triggers: ["trigger1 (weightage1)", "trigger2 (weightage2)", "trigger3 (weightage3)", "trigger4 (weightage4)", "trigger5 (weightage5)"]
            Competitors: ["competitor1", "competitor2", "competitor3", "competitor4", "competitor5"]

            Examples:

            1. Domain: Artificial Intelligence
               Project: GPT Model Comparison
               Description: Comprehensive research on performance differences between GPT models...
               Effective Triggers: ["accuracy (90)", "speed (85)", "cost-effectiveness (80)", "use-case advantages (75)", "scalability (70)"]
               Competitors: ["OpenAI", "Anthropic", "Google", "Microsoft", "Hugging Face"]

            2. Domain: Healthcare
               Project: Telemedicine Adoption
               Description: Analyze the adoption of telemedicine platforms...
               Effective Triggers: ["patient satisfaction (95)", "cost savings (90)", "technological barriers (85)", "accessibility (80)", "health outcomes (75)"]
               Competitors: ["Teladoc", "Amwell", "Doctor on Demand", "MDLive", "Practo"]

            3. Domain: Renewable Energy
               Project: Solar Panel Efficiency
               Description: Research the latest advancements in solar panel technology...
               Effective Triggers: ["efficiency improvements (90)", "cost reduction (85)", "environmental impact (80)", "durability (75)", "energy output (70)"]
               Competitors: ["First Solar", "SunPower", "Canadian Solar", "JinkoSolar", "Trina Solar"]

            4. Domain: E-commerce
               Project: Customer Retention Strategies
               Description: Investigate effective customer retention strategies for e-commerce platforms...
               Effective Triggers: ["personalized marketing (95)", "loyalty programs (90)", "post-purchase engagement (85)", "customer feedback (80)", "discounts (75)"]
               Competitors: ["Amazon", "Shopify", "Walmart", "eBay", "Alibaba"]

            Now, extract the top 5 effective triggers with weightage and top 5 competitors for:

            Domain: {domain}
            Project: {project}
            Description: {description}
            """
            triggers_competitors_response = self.llm.predict(triggers_competitors_prompt)
            
            # Parse responses
            effective_triggers, competitors = self.parse_triggers_competitors(triggers_competitors_response)
            
            # Prompt for word cloud data (changed to 20 keywords with scores)
            word_cloud_prompt = f"""
        Given the domain, project, and description, extract the top 20 keywords or phrases for a word cloud.

        Format your response exactly as follows:
        Word Cloud Data: ["keyword1", "keyword2", ..., "keyword20"]

        Examples:

        1. Domain: Artificial Intelligence
           Project: GPT Model Comparison
           Description: Comprehensive research on performance differences between GPT models...
           Word Cloud Data: ["GPT models", "accuracy", "speed", "cost-effectiveness", "use-case advantages", "scalability", "real-world applications", "performance", "comparison", "Claude", "language models", "AI", "machine learning", "NLP", "deep learning", "natural language processing", "model efficiency", "inference time", "training time", "hyperparameters", "neural networks", "transformers", "language understanding", "text generation", "AI research", "model evaluation", "benchmarking", "technological advancements", "artificial intelligence", "machine intelligence"]

        2. Domain: Healthcare
           Project: Telemedicine Adoption
           Description: Analyze the adoption of telemedicine platforms...
           Word Cloud Data: ["telemedicine", "patient satisfaction", "cost savings", "technological barriers", "rural areas", "healthcare", "adoption", "platforms", "accessibility", "health outcomes", "remote care", "telehealth", "virtual consultations", "health tech", "digital health", "patient engagement", "healthcare providers", "telemedicine platforms", "healthcare innovation", "telemedicine adoption", "healthcare technology"]

        3. Domain: Renewable Energy
           Project: Solar Panel Efficiency
           Description: Research the latest advancements in solar panel technology...
           Word Cloud Data: ["solar panels", "efficiency improvements", "cost reduction", "environmental impact", "renewable energy", "technology", "durability", "energy output", "sustainability", "advancements", "solar energy", "photovoltaic cells", "solar power", "clean energy", "energy storage", "solar technology", "solar innovation", "solar efficiency", "solar advancements", "solar research", "solar industry"]

        4. Domain: E-commerce
           Project: Customer Retention Strategies
           Description: Investigate effective customer retention strategies for e-commerce platforms...
           Word Cloud Data: ["customer retention", "personalized marketing", "loyalty programs", "post-purchase engagement", "e-commerce", "strategies", "customer feedback", "discounts", "platforms", "retention", "customer satisfaction", "customer experience", "retention strategies", "customer loyalty", "e-commerce platforms", "customer engagement", "marketing strategies", "customer behavior", "e-commerce trends", "customer retention techniques", "e-commerce growth"]

        Now, extract the top 20 keywords or phrases for a word cloud for:

        Domain: {domain}
        Project: {project}
        Description: {description}
        """
            word_cloud_response = self.llm.predict(word_cloud_prompt)
            word_cloud_data = self.parse_word_cloud(word_cloud_response)
            pain_points_prompt = f"""
            Given the domain, project, and description, extract the top 10 pain points users face with existing competitors.

            Format your response exactly as follows:
            Pain Points: ["pain_point1", "pain_point2", ..., "pain_point10"]

            Examples:

            1. Domain: Artificial Intelligence
               Project: GPT Model Comparison
               Description: Comprehensive research on performance differences between GPT models...
               Pain Points: ["high cost", "slow response times", "lack of customization", "poor customer support", "limited use cases", "complex integration", "data privacy concerns", "inconsistent performance", "lack of transparency", "difficulty in scaling"]

            2. Domain: Healthcare
               Project: Telemedicine Adoption
               Description: Analyze the adoption of telemedicine platforms...
               Pain Points: ["technical glitches", "lack of personal interaction", "limited insurance coverage", "data security concerns", "poor user experience", "limited availability of specialists", "high costs", "lack of integration with existing systems", "difficulty in accessing rural areas", "regulatory challenges"]

            3. Domain: Renewable Energy
               Project: Solar Panel Efficiency
               Description: Research the latest advancements in solar panel technology...
               Pain Points: ["high upfront costs", "low efficiency in cloudy weather", "maintenance challenges", "limited storage capacity", "environmental concerns", "lack of government incentives", "difficulty in installation", "inconsistent energy output", "long payback periods", "lack of awareness"]

            4. Domain: E-commerce
               Project: Customer Retention Strategies
               Description: Investigate effective customer retention strategies for e-commerce platforms...
               Pain Points: ["poor customer service", "lack of personalized experiences", "high shipping costs", "difficulty in returns", "lack of trust", "limited payment options", "poor website performance", "lack of loyalty programs", "inconsistent product quality", "difficulty in finding products"]

            Now, extract the top 10 pain points users face with existing competitors for:

            Domain: {domain}
            Project: {project}
            Description: {description}
            """
            pain_points_response = self.llm.predict(pain_points_prompt)
            pain_points_data = self.parse_pain_points(pain_points_response)
            
            # Combine all results
            final_results = {
                'domain': domain,
                'project': project,
                'description': description,
                'effective_triggers': effective_triggers,
                'competitors': competitors,
                'word_cloud_data': word_cloud_data,  # Now includes normalized word scores
                'pain_points': pain_points_data,  # Pain points without scores
                'full_analysis': refined_analysis,  # Refined analysis from DataStax
                'timestamp': datetime.now().isoformat(),
                'resource_links': resource_links  # Added resource links
            }
            
            return final_results
        except Exception as e:
            print(f"Error in analysis: {e}")
            return {"error": str(e)}

def main():
    analyzer = ResearchAnalyzer(
        groq_api_key="YOUR_GROQ_API_KEY",
        google_api_key="YOUR_GOOGLE_API_KEY",
        google_cse_id="YOUR_CSE_ID"
    )
    
    domain = "Artificial Intelligence"
    project = "GPT Model Comparison"
    description = """
    Comprehensive research on performance differences between GPT models 
    (GPT-3, GPT-4, Claude, etc.) in real-world applications, focusing on accuracy, 
    speed, cost-effectiveness, and specific use-case advantages.
    """
    
    results = analyzer.analyze(domain, project, description)
    
    print(json.dumps(results, indent=2))
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"research_results_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"Full results saved to {output_file}")

if __name__ == "__main__":
    main()

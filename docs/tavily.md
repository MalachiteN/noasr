为实现 Tavily 工具，下面是 Tavily Python SDK 例子：

为使用 Tavily 项目需引入 tavily-python 依赖项。

发起请求示例：

```python
# To install: pip install tavily-python
from tavily import TavilyClient
client = TavilyClient("tvly-dev-一串字母数字")
response = client.search(
    query="what is tavily",
    include_answer="basic",
    search_depth="advanced"
)
print(response)
```

这是没抛异常的时候应该能拿到的 JSON 响应：

```json
{
  "query": "what is tavily",
  "response_time": 2.15,
  "follow_up_questions": null,
  "answer": "Tavily is a specialized search engine for AI agents, providing real-time, accurate, and unbiased information. It offers APIs for search, extraction, and crawling of web data. Tavily focuses on optimizing search for large language models and AI agents.",
  "images": [],
  "results": [
    {
      "url": "https://learn.microsoft.com/en-us/connectors/tavily/",
      "title": "Tavily (Independent Publisher) - Connectors - Microsoft Learn",
      "content": "# Tavily (Independent Publisher) (Preview)\n\nTavily is a specialized search engine designed for Large Language Models (LLMs) and AI agents. It provides real-time, accurate, and unbiased information, enabling AI applications to retrieve and process data efficiently. Tavily is built with AI developers in mind, simplifying the process of integrating dynamic web information into AI-driven solutions.\n\nThis connector is available in the following products and regions:",
      "score": 0.9405774,
      "raw_content": null,
      "favicon": "https://learn.microsoft.com/favicon.ico"
    },
    {
      "url": "https://www.tavily.com/blog/tavily-101-ai-powered-search-for-developers",
      "title": "Tavily 101: AI-powered Search for Developers",
      "content": "## What is Tavily?\n\nTavily is the web access layer for AI agents. It is a single API for agents to search, extract, and crawl the live web in formats designed specifically for RAG and agent workflows.\n\nUnlike traditional search engines that’s built for humans, Tavily is built for AI systems. It provides:\n\n Fresh, grounded results optimized for LLM ingestion\n Low-latency even at production scale, powered by dynamic caching and an agent-native index\n Agent-native firewall to prevent against prompt injection and data leakage\n\n## The Endpoints: Search, Extract, and Crawl\n\nDuring the live coding demo, we walked through the three main ways you can interact with the web using the Tavily Python SDK.\n\n### 1. /search - find and rank sources [...] Join our live event on April 7th to learn how to build with Tavily! Register Here\n\nWebinarsBlogCertification\n\nengineering4 min read\n\n# Tavily 101: AI-powered Search for Developers\n\nTavily is the web access layer built for AI agents, helping developers bridge the gap between static language models and the live internet. With a single API, you can search, extract, and crawl real-time web data in formats optimized for RAG and agent workflows, with low latency and built-in safety. In this Tavily 101 recap, we break down when to use each endpoint, the real-world agent patterns they unlock, and a first look at the new Research API for end-to-end automated web research.\n\nShubhendra Singh Chauhan\n\nBy Shubhendra Singh Chauhan\n\nJanuary 28, 2026\n\nTavily 101: AI-powered Search for Developers [...] By combining semantic search, scalable extraction, intelligent crawling, and enterprise grade security, Tavily provides the foundation for the next generation of AI systems.\n\nIf you are ready to get started, explore the full session, experiment with the Tavily playground, and begin building agents that can truly search, read, and research the live web.\n\n Watch the event: \n Sign up at  to get your API key\n Explore the docs:",
      "score": 0.9210814,
      "raw_content": null,
      "favicon": "https://www.tavily.com/favicon.ico"
    },
    {
      "url": "https://docs.tavily.com/documentation/about",
      "title": "About - Tavily Docs",
      "content": "Building an AI agent that leverages realtime online information is not a simple task. Scraping doesn’t scale and requires expertise to refine, current search engine APIs don’t provide explicit information to queries but simply potential related articles (which are not always related), and are not very customziable for AI agent needs. This is why we’re excited to introduce the first search engine for AI agents - Tavily. Tavily is a search engine optimized for LLMs, aimed at efficient, quick and persistent search results. Unlike other search APIs such as Serp or Google, Tavily focuses on optimizing search for AI developers and autonomous AI agents. We take care of all the burden of searching, scraping, filtering and extracting the most relevant information from online sources. All in a [...] content to your task, query or goal. In addition, Tavily allows developers to add custom fields such as context and limit response tokens to enable the optimal search experience for LLMs. Tavily can also help your AI agent make better decisions by including a short answer for cross-agent communication. [...] If you’re an AI developer looking to integrate your application with our API, or seek increased API limits, please reach out!\n\n## ​ Why choose Tavily?\n\nTavily shines where others fail, with a Search API optimized for LLMs.\n\nPurpose-Built\n\nTailored just for LLM Agents, we ensure the search results are optimized for RAG. We take care of all the burden in searching, scraping, filtering and extracting information from online sources. All in a single API call! Simply pass the returned search results as context to your LLM.\n\nVersatility\n\nBeyond just fetching results, the Tavily Search API offers precision. With customizable search depths, domain management, and parsing HTML content controls, you’re in the driver’s seat.\n\nPerformance",
      "score": 0.91137725,
      "raw_content": null,
      "favicon": "https://docs.tavily.com/mintlify-assets/_mintlify/favicons/tavilyai/SXaxSfweEU3ftIlh/_generated/favicon/apple-touch-icon.png"
    },
    {
      "url": "https://composio.dev/content/tavily-api-ai-agents-introduction",
      "title": "Introduction to Using Tavily Search API with AI Agents - Composio",
      "content": "With Tavily, you can scale your AI systems while delivering faster, more accurate search results. But what specific features set Tavily apart? Let’s explore.\n\nFunctionality and Features\n\nNow that you know what Tavily is, it’s time to uncover the features that make it indispensable for AI developers.\n\nTavily is a gateway to more intelligent data management. The API supports natural language queries, so users can interact with your system as if talking to a human. It also offers the following features.\n\nAdvanced Filtering: Fine-tune search parameters for precise results.\n\nContextual Search: Ensure every query delivers relevant outcomes.\n\nReal-Time Updates: Keep your results accurate and timely. [...] Let’s dive into how to integrate Tavily API using AI agents and what makes Tavily Search API a powerful tool for your AI systems.\n\n## What is Tavily Search API?\n\nBefore you can fully leverage Tavily in your AI projects, it’s essential to understand what the API is and how it works.\n\nOverview of Tavily Search API\n\nIf you’re looking for a reliable way to enhance your AI agents’ search capabilities, the Tavily Search API is the answer.\n\nTavily\n\nThe Tavily Search API is a specialized search engine for large language models (LLMs) and AI agents. It provides real-time, accurate, and unbiased information, enabling AI applications to retrieve and process data efficiently. Tavily is built with AI developers in mind, simplifying the integration of dynamic web information into AI-driven solutions. [...] Composio enables faster deployment of Tavily’s advanced search capabilities within your AI systems by automating repetitive tasks and offering customizable options. This efficiency empowers developers to focus on innovation while delivering exceptional performance.\n\nLet’s wrap up with a quick recap and a glimpse into what’s next.\n\n## Conclusion\n\nThe Tavily Search API is your go-to solution for enhancing AI agents. It simplifies natural language queries, handles complex filtering, and delivers real-time results. Integrating Tavily API with AI Agents allows you to build more innovative, responsive systems that meet your users’ needs.\n\nBut the journey doesn’t end here.",
      "score": 0.8993429,
      "raw_content": null,
      "favicon": "https://composio.dev/apple-touch-icon.png"
    },
    {
      "url": "https://docs.tavily.com/faq/faq",
      "title": "Frequently Asked Questions - Tavily Docs",
      "content": "Tavily offers three different endpoints:\n\n Tavily Search API - A search engine designed for AI agents, combining search and scraping capabilities.\n Tavily Extract API - Scrape up to 20 URLs in a single API call.\n Tavily Crawl API - Map and crawl domains efficiently.\n\n \n\nWhat is Tavily Search API?\n\nTavily Search API is a specialized search engine designed for LLMs and AI agents. It provides real-time, customizable, and RAG-ready search results and extracted content, enabling AI applications to retrieve and process data efficiently.\n\n \n\nHow is Tavily Search API different from other search APIs? [...] Tavily Docs home page\n\nHomeIntroductionAPI & SDKsEcosystemExamplesChangelogHelp\n\n API Playground\n Community\n Blog\n\n##### Getting Started\n\n About\n Quickstart\n Credits & Pricing\n Rate Limits\n\n##### FAQ\n\n Frequently Asked Questions\n\n Features & Benefits\n Pricing & Plans\n Integration & Usage\n Support & Privacy\n Getting Started\n\nFAQ\n\n# Frequently Asked Questions\n\nWhat is Tavily?\n\nTavily allows your AI agent to access the web, securely, and at scale. Supercharge your AI agent with real-time search, scraping, and structured data retrieval in a single API call. Tavily simplifies the process of integrating dynamic web information into AI-driven solutions.\n\n \n\nWhat APIs does Tavily offer?\n\nTavily offers three different endpoints: [...] What is GPT Researcher, and how does it relate to Tavily?\n\nGPT Researcher is an open-source, autonomous research agent powered by Tavily’s Search API. It automates the research process by retrieving, filtering, and synthesizing data from over 20 web sources per task.\n\n#### ​ Support & Privacy\n\nWhat level of support does Tavily provide?\n\n Paid Subscriptions – Email support via support@tavily.com.\n Enterprise Plan – White-glove support including:\n  + Personal Slack channel\n  + Dedicated account manager\n  + AI engineer for technical assistance and optimizations\n  + Uptime and support SLAs\n\n \n\nWhere can I find Tavily’s privacy policy?\n\nTavily’s privacy policy is available here, outlining how data is handled and ensuring compliance with global regulations.",
      "score": 0.8863518,
      "raw_content": null,
      "favicon": "https://docs.tavily.com/mintlify-assets/_mintlify/favicons/tavilyai/SXaxSfweEU3ftIlh/_generated/favicon/apple-touch-icon.png"
    }
  ],
  "request_id": "9712b21b-e90f-4197-94b4-a116f58fd17d"
}
```

而这是 tavily 模块的所有内置错误的示例：

```python
# /usr/local/lib/python3.11/site-packages/tavily/errors.py
class UsageLimitExceededError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class BadRequestError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class ForbiddenError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class InvalidAPIKeyError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class TimeoutError(Exception):
    def __init__(self, timeout: float):
        super().__init__(f"Request timed out after {timeout} seconds.")


class MissingAPIKeyError(Exception):
    def __init__(self):
        super().__init__(
            "No API key provided. Please provide the api_key attribute or set the TAVILY_API_KEY environment variable."
        )
```

你需要在 config.json 引入一个 tavily_api_key 的字段，用来加载 tavily API Key 给这个工具用。

这个返回的 JSON你不用怎么处理怎么格式化的，直接按原始 JSON 字符串喂给模型就行了，LLM非常能理解这种结构化文本。

当你捕获到API错误了，也直接把错误原因字符串传递给 LLM。
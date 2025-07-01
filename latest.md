# Summary of “The new skill in AI is not prompting, it's context engineering”

The Hacker News article titled "The new skill in AI is not prompting, it's context engineering" highlights a shift in the AI community's focus from the traditional skill of prompt engineering — crafting specific text instructions to AI models — towards "context engineering." 

🧠 **What is Context Engineering?** Context engineering involves carefully organizing, structuring, and providing the right amount of relevant information (context) to an AI model (especially Large Language Models or LLMs) so it can generate accurate and useful outputs. Unlike prompt engineering, which looks at the immediate input, context engineering considers the broader information environment, including examples, documentation, prior conversations, and potentially tool usage instructions.

🔧 **Technical Insight:**
- LLMs operate better when given relevant, precise context rather than vague or minimal prompts.
- Managing context includes techniques like context pruning (removing irrelevant data), summarization, quarantine (isolating certain context parts), and tool loadouts (providing the model with the right external tools it can use).
- This approach is analogous to how software engineers manage requirements and documentation to build complex projects.

💬 **Community Discussion Highlights:**

- **Authenticity & Skepticism:** Some community members view "context engineering" as a rebranding of prompt engineering buzzwords, expressing skepticism about the hype and terminology ([comment 44428463](https://news.ycombinator.com/item?id=44428463)). Others appreciate the clearer, more practical techniques emerging around managing context rather than just prompt wording ([comment 44428606](https://news.ycombinator.com/item?id=44428606)).

- **Practical Usage:** Developers shared examples where providing detailed context enables LLMs to perform impressive tasks like writing code in unfamiliar codebases or automating parts of software development ([comment 44429764](https://news.ycombinator.com/item?id=44429764)), ([comment 44428045](https://news.ycombinator.com/item?id=44428045)).

- **Limits & Realism:** Several users noted that LLMs still fail even with good context, highlighting current limitations and emphasizing the need for human review ([comment 44429043](https://news.ycombinator.com/item?id=44429043)), ([comment 44429090](https://news.ycombinator.com/item?id=44429090)). The ongoing dialogue stresses that context engineering is vital but not a magical fix.

- **Future of AI Development:** Some commentators believe future LLMs will incorporate more autonomy in gathering context themselves (e.g., tool use, web search), potentially reducing the manual context engineering burden ([comment 44429807](https://news.ycombinator.com/item?id=44429807)). Meanwhile, others argue that context engineering represents a broader product development or software engineering skill rather than something uniquely AI-related ([comment 44428507](https://news.ycombinator.com/item?id=44428507)).

🌟 **Why is this popular?** The conversation resonates as AI tools become more integrated into software development and enterprise applications. People realize that simply typing prompts isn’t enough — providing structured, relevant context is critical to unlocking the real power of AI. This creates a new skill set for developers, product managers, and AI practitioners.

🔗 **Useful Links:**
- Original article: [https://www.philschmid.de/context-engineering](https://www.philschmid.de/context-engineering)
- Hacker News discussion: [https://news.ycombinator.com/item?id=44427757](https://news.ycombinator.com/item?id=44427757)
- Google Search on "Context Engineering in AI": [https://www.google.com/search?q=context+engineering+ai](https://www.google.com/search?q=context+engineering+ai)
- Google Search on "Prompt Engineering": [https://www.google.com/search?q=prompt+engineering](https://www.google.com/search?q=prompt+engineering)

📝 **Simple example:**
> Instead of asking an AI "Write a to-do app," context engineering involves providing extra details like examples of existing code, the programming language, UI requirements, and project conventions. This gives the AI the context needed to produce more accurate and suitable code.

To get started with context engineering, one might learn about related topics such as **Large Language Models (LLMs)**, **prompt engineering**, **RAG (Retrieval-Augmented Generation)**, and **tool integration with AI**.
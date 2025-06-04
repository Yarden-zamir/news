# Overview
Quarkdown is a modern typesetting system built on top of Markdown, aiming to provide more powerful and flexible document formatting and publishing capabilities. It combines the simplicity of Markdown with enhanced features often found in complex typesetting languages like LaTeX and Typst, but tries to remain approachable.

# Technical Info
- **Foundation:** Based on Markdown, adding syntax for functions and layout control.
- **Implementation:** Uses Kotlin and JVM (requiring Java 17+), which some users feel may affect ease of adoption.
- **Output:** Converts Markdown-style inputs to HTML and PDF using Puppeteer and Chrome's print-to-PDF capabilities.
- **Features:** Supports template functions, scripting-like constructs, basic typesetting controls. The syntax introduces function calls using dots and braces (e.g., `.function {arg}`), which differs from plain Markdown.

# Popularity Factors
- **Simplicity + Power:** Addresses Markdown's limitations by introducing more control without jumping fully to complex languages like LaTeX.
- **Markdown Compatibility:** While not fully Markdown-compatible, it leverages Markdown's lightweight approach.
- **Community Interest:** People excited about an alternative to LaTeX and Typst for scientific and academic documents.

# Community Conversation Highlights
- **Comparison to Typst and LaTeX:** Many compare Quarkdown to Typst and LaTeX, debating which is easier to use or more powerful. Typst is praised for clean syntax and powerful features but is considered more complex to learn; LaTeX remains the gold standard for academia due to stability and ecosystem maturity ([44167973](https://news.ycombinator.com/item?id=44167973), [44167666](https://news.ycombinator.com/item?id=44167666), [44171671](https://news.ycombinator.com/item?id=44171671)).
- **Syntax Concerns:** Some users find Quarkdown’s syntax off-putting or less Markdown-like, raising concerns about readability and learning curve ([44167875](https://news.ycombinator.com/item?id=44167875), [44167712](https://news.ycombinator.com/item?id=44167712)).
- **JVM/Java Requirement:** The need for Java and Kotlin is seen as a barrier for some, especially preferring static binaries ([44168050](https://news.ycombinator.com/item?id=44168050), [44169864](https://news.ycombinator.com/item?id=44169864)).
- **Ecosystem and Templates:** Worries about lack of publisher or community templates could limit adoption, especially in scientific publishing ([44167856](https://news.ycombinator.com/item?id=44167856), [44170962](https://news.ycombinator.com/item?id=44170962)).
- **Alternatives Mentioned:** Quarto, Pandoc, Typst, and other systems get notable mentions as existing or competing options that offer various trade-offs in power, ease of use, and compatibility ([44167690](https://news.ycombinator.com/item?id=44167690), [44167713](https://news.ycombinator.com/item?id=44167713), [44169235](https://news.ycombinator.com/item?id=44169235)).
- **Longevity and Stability:** Some users value LaTeX’s decades-long stability and robust package ecosystem, questioning how Quarkdown will fare long-term ([44170528](https://news.ycombinator.com/item?id=44170528), [44171671](https://news.ycombinator.com/item?id=44171671), [44169344](https://news.ycombinator.com/item?id=44169344)).

# Sentiment Summary
😊 Enthusiasm for a new typesetting system that might simplify producing high-quality PDFs and docs while retaining Markdown’s ease.
🤔 Some skepticism about syntax complexity, lack of ecosystem, and platform requirements.
⚠️ Concerns on whether it can replace well-established tooling like LaTeX and Typst.

# Why Should Newcomers Care?
Markdown is widely used for quick note-taking and writing on the web, but it has limitations, especially for complex documents like research papers, reports, or books. Quarkdown attempts to offer a bridge from simple Markdown to a more powerful typesetting environment without the steep learning curve of LaTeX. Understanding these tools helps newcomers select the right typesetting tool depending on their document complexity and workflow.

# Example Usage
A function call in Quarkdown might look like this:

    .greet {world} from:{iamgio}

This syntax is used to define and call functions with arguments inside the document to control layout and content dynamically.

# Additional Resources for Learning
- [Markdown](https://www.google.com/search?q=markdown)
- [LaTeX](https://www.google.com/search?q=latex+typesetting)
- [Typst](https://www.google.com/search?q=typst+typesetting)
- [Pandoc](https://www.google.com/search?q=pandoc)
- [Quarto](https://www.google.com/search?q=quarto+document+system)

# Links
- Quarkdown repository: https://github.com/iamgio/quarkdown
- Hacker News discussion: https://news.ycombinator.com/item?id=44167592
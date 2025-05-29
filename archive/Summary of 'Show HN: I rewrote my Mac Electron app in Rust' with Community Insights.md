# Summary

The article presents a developer's journey of rewriting their Mac desktop application from Electron to Rust using Tauri. The original Electron app was quite large (close to 1GB) and had performance bottlenecks despite Electron's popularity for cross-platform desktop app development. By switching to Rust with Tauri, the team achieved significantly smaller binary sizes (~15-25MB) and better performance, especially for their media indexing and search application.

The choice of Rust and Tauri was motivated by the desire for cross-platform support (starting with Apple Silicon Macs) and leveraging Rust's efficiency for computation-intensive tasks such as ML model inference using ONNX Runtime. The rewrite also allowed the team to bundle native Redis modules for vector search embeddings, which proved more effective than alternatives like SQLite vector extensions for their use case.

# Technical Highlights

- **Electron vs Tauri:** Electron bundles a full Chromium browser, resulting in large app sizes. Tauri uses native system webviews (Safari WKWebView on Mac, WebView2 on Windows), making app sizes much smaller, but at the cost of cross-platform rendering inconsistencies.
  - [Learn more about Electron vs Tauri](https://www.google.com/search?q=Electron+vs+Tauri+desktop+apps)

- **Rust Backend:** The app backend and core processing are written in Rust, offering performance benefits and more maintainable code compared to Node.js in Electron.
  - [Introduction to Rust](https://www.google.com/search?q=Rust+programming+language)

- **ONNX Runtime:** Used for machine learning model inference (specifically CLIP models for image embedding), integrated using the Ort crate in Rust.
  - [ONNX Runtime](https://www.google.com/search?q=ONNX+Runtime)

- **Redis for Vector Storage:** The team embedded Redis to store vector embeddings for fast similarity searches, outperforming SQLite in their scenario.
  - [Redis Vector Search](https://www.google.com/search?q=Redis+Vector+Search)

- **Cross-Platform Challenges:** System webviews cause UI inconsistencies across OSes. Electron provides consistent UI by embedding Chromium but with larger binaries.

# Why the Article is Popular 🚀

- **Real-world challenge:** The transition from Electron to Rust tackles a common pain point of app size, performance, and cross-platform support.
- **Tech stack clash:** Contrasts popular Electron and newer Rust-based Tauri approaches, sparking debate about trade-offs.
- **Performance Gains:** Demonstrates concrete improvements in app size and responsiveness.
- **Community Engagement:** Generates rich discussions on cross-platform UI challenges, ML integration, and developer experience.

# Community Conversation Highlights 💬

- **Rendering Challenges:** Many developers shared frustrations with Tauri's use of native system webviews causing UI inconsistencies and complex cross-platform testing effort. Some find Electron's bundled Chromium easier despite size concerns ([comment 44118478](https://news.ycombinator.com/item?id=44118478), [44118251](https://news.ycombinator.com/item?id=44118251)).
- **Rust Adoption:** Developers appreciate Rust's performance and safety, but some note the learning curve and ecosystem immaturity for desktop UI compared to JavaScript frameworks ([comment 44118644](https://news.ycombinator.com/item?id=44118644), [44120143](https://news.ycombinator.com/item?id=44120143)).
- **ML Integration:** Discussion on embedding models like CLIP using ONNX Runtime and other Rust crates like burn and candle; Redis chosen for vector search due to performance ([comment 44118276](https://news.ycombinator.com/item?id=44118276), [44118423](https://news.ycombinator.com/item?id=44118423)).
- **UI Framework Choices:** Some debate the merits of Flutter, egui, and other Rust-native GUI frameworks versus web-based UIs (Tauri/Electron), noting trade-offs in native feel versus ecosystem maturity ([comment 44118885](https://news.ycombinator.com/item?id=44118885), [44119109](https://news.ycombinator.com/item?id=44119109)).
- **Pricing and Access:** Community members request trials/demo before purchase and clarification on pricing and refund policies ([comment 44118592](https://news.ycombinator.com/item?id=44118592), [44119374](https://news.ycombinator.com/item?id=44119374)).

# Sentiments

- **Positive:** Many praise the performance gains and appreciate open discussion of trade-offs.
- **Critical:** Some express concerns about inconsistencies due to relying on system webviews and the difficulty of cross-platform UI testing.
- **Curious:** Interest in technical details regarding ML model integration and vector search implementation.

# Simple Usage Example

While the original project is specific and complex, a simple Rust + Tauri app example to get started can be found here:

- [Tauri Getting Started](https://tauri.app/v1/guides/getting-started/prerequisites/)

# Links

- Original article: [desktopdocs.com](https://desktopdocs.com/?v=2025)
- Hacker News Thread: [Show HN: I rewrote my Mac Electron app in Rust (HN)](https://news.ycombinator.com/item?id=44118023)

---

This summary is tailored for new tech enthusiasts and provides links to learn more about essential terms and technologies involved:
- [Rust programming language](https://www.google.com/search?q=Rust+programming+language)
- [Electron framework](https://www.google.com/search?q=Electron+app+framework)
- [Tauri framework](https://www.google.com/search?q=Tauri+framework)
- [ONNX Runtime](https://www.google.com/search?q=ONNX+Runtime)
- [Redis Vector Search](https://www.google.com/search?q=Redis+Vector+Search)

Feel free to explore these as starting points.

---
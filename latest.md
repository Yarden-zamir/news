The article "How to modify Starlink Mini to run without the built-in WiFi router" by LorenDB explores a technical modification to the Starlink Mini satellite internet device. Starlink Mini is designed by SpaceX to provide satellite internet with a built-in WiFi router. The author discusses how to remove or disable the internal WiFi router completely to prevent any WiFi signals, which could be critical for use cases where stealth or reduced power consumption is necessary.

🔧 **Technical Context:**
- The Starlink Mini includes an Ethernet jack and WiFi board. While the WiFi router can be turned off in settings, some users want to physically disable or remove the WiFi to ensure no signals are emitted during power-on or unexpected resets.
- The device uses modulated board-to-board Ethernet instead of direct RGMII from MAC to MAC, as discussed by community experts. This design choice eases prototyping and integration but raises questions about complexity and power consumption.
- Comments discuss alternatives and the engineering trade-offs involved, such as using Ethernet PHYs, handling signal integrity, and cost-saving tactics like removing isolation transformers.

🌟 **Why Popular?**
- Starlink has gained huge attention for its revolutionary satellite internet capabilities, especially in areas with limited infrastructure.
- The modification addresses specific use cases like drones or front-line deployment in conflict zones (notably Ukraine), where reducing WiFi emissions can be crucial for safety and operational security.
- The post ties into broader geopolitical and military themes, as seen by references to Ukraine, Russia, and the Starlink usage in warfare, which engages a wide audience.

🗨️ **Community Conversation Highlights:**
- Many comments debate the speed limits and reliability of Starlink for fast-moving platforms such as drones ([comment 44282710](https://news.ycombinator.com/item?id=44282710), [44284504](https://news.ycombinator.com/item?id=44284504)).
- Discussions around US government involvement with Starlink provision in Ukraine and the geopolitical implications ([comments 44283021](https://news.ycombinator.com/item?id=44283021), [44282936](https://news.ycombinator.com/item?id=44282936)).
- Technical debates on Ethernet interfaces, specifically why modulated Ethernet was chosen over direct RGMII signals board-to-board ([comments 44283103](https://news.ycombinator.com/item?id=44283103), [44282587](https://news.ycombinator.com/item?id=44282587), [44283689](https://news.ycombinator.com/item?id=44283689)).
- Concerns about the practicality of complete WiFi removal to ensure stealth in certain environments ([comments 44283397](https://news.ycombinator.com/item?id=44283397), [44283526](https://news.ycombinator.com/item?id=44283526)).

😊 **Sentiments:** Most community members show a mix of technical curiosity and real-world application interest, especially regarding military and security use cases. There is also recognition of the challenges and compromises in hardware design.

🔗 **Sources:**
- Original article: [How to modify Starlink Mini](https://olegkutkov.me/2025/06/15/how-to-modify-starlink-mini-to-run-without-the-built-in-wifi-router/)
- Hacker News discussion: [HN Thread](https://news.ycombinator.com/item?id=44282017)

💡 **For Beginners:**
- If you want to learn more about [Starlink](https://www.google.com/search?q=Starlink+satellite+internet), [Ethernet PHY](https://www.google.com/search?q=Ethernet+PHY), and [RGMII](https://www.google.com/search?q=RGMII+interface), these terms explain satellite internet technology and networking protocols used in devices like Starlink Mini.

👾 **Example Use-Case:**
A drone operator in a conflict zone might remove the WiFi from their Starlink Mini to avoid any WiFi emissions that could be detected by adversaries, while maintaining reliable satellite internet connectivity via the device’s Ethernet connection.

This discussion helps enthusiasts and professionals understand hardware modifications for satellite internet devices, the balance between design and real-world operational needs, and the geopolitical context in which these technologies are used.
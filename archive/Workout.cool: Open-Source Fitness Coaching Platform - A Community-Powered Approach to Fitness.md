# Summary of Workout.cool - Open-Source Fitness Coaching Platform

Workout.cool is an open-source project aiming to provide a transparent, free, and customizable fitness coaching platform. Built with TypeScript and a PostgreSQL backend, it offers a web-based Progressive Web App (PWA) experience for users to select exercises targeting specific muscles and equipment, create workouts, save routines, and potentially share them publicly.

## Technical Insights ⚙️
- The project rebuilt an earlier app (workout.lol) from scratch to improve maintainability, scalability, and fix licensing ambiguities, especially related to videos and exercise datasets.
- Uses a SQL-based backend (PostgreSQL) for flexibility, advanced filtering, and full-text search.
- Embeds exercise videos from a partner with legal permission—creating original high-quality 3D exercise animations is costly (~€10–20 per animation).
- Architecture designed for easy creation, reuse, sharing, and analysis of training blocks.
- Open to integrations with fitness platforms like Strava, Garmin, HealthKit ([comment 44311247](https://news.ycombinator.com/item?id=44311247)).

## Why is it Popular? 🚀
- Provides a much-needed free and open alternative in an ecosystem dominated by paid, closed, or buggy apps.
- Tailored for people overwhelmed by complexity in fitness apps—aiming to be beginner-friendly and transparent.
- Responds quickly to community feedback, plans for features like saving/tracking routines, community sharing, and open APIs.
- Gained attention because the original app was abandoned, and this project revived the open spirit with improvements.

## Community Conversation Summary 💬

### Positives 👍
- Many appreciate the open-source nature and community-driven development approach ([comments 44310697](https://news.ycombinator.com/item?id=44310697), [44311400](https://news.ycombinator.com/item?id=44311400)).
- Users find muscle selection feature helpful compared to many commercial apps ([44309743](https://news.ycombinator.com/item?id=44309743)).
- Enthusiasm for future features like saving, sharing routines, and API integration ([44311247](https://news.ycombinator.com/item?id=44311247)).
- Experienced developers and trainers finding it useful for custom setups or as a component of larger systems ([44311281](https://news.ycombinator.com/item?id=44311281)).

### Constructive Criticism & Suggestions 🛠️
- Current exercise recommendation logic lacks proper programming principles, leading to impractical workouts (e.g., too many exercises, poor exercise selection order) ([44312313](https://news.ycombinator.com/item?id=44312313)).
- Beginners may find muscle-based filtering complex; suggestions to add beginner-friendly presets like "full body", goals-based entry points like "fat loss", and optional filters ([44311212](https://news.ycombinator.com/item?id=44311212), [44311561](https://news.ycombinator.com/item?id=44311561), [44310237](https://news.ycombinator.com/item?id=44310237)).
- Some users raised concerns about safety and proper form, especially for novices ([44310132](https://news.ycombinator.com/item?id=44310132)).
- Server backend occasionally struggled with unexpected heavy traffic from Hacker News, leading to errors on loading exercises ([44310423](https://news.ycombinator.com/item?id=44310423), [44310031](https://news.ycombinator.com/item?id=44310031)).

### Lively Discussions 🔥
- Debate around 5x5 workout programs and their modern applicability ([44312682](https://news.ycombinator.com/item?id=44312682), [44310861](https://news.ycombinator.com/item?id=44310861)).
- Licensing issues and rationale behind starting fresh rather than forking the original app ([44310406](https://news.ycombinator.com/item?id=44310406), [44310400](https://news.ycombinator.com/item?id=44310400)).
- Future ideas around integrating AI for personalized workout suggestions and community contributions ([44311536](https://news.ycombinator.com/item?id=44311536)).

## For the Tech-Newbie 🤓
If you're curious about fitness apps and open-source software, Workout.cool is a great example where technology meets health. It’s like a free fitness coach on your phone or computer, designed with community help and transparency. 

Want to learn more about the technical terms? Check out these Google searches:
- [Progressive Web Apps (PWA)](https://www.google.com/search?q=Progressive+Web+Apps)
- [TypeScript](https://www.google.com/search?q=TypeScript)
- [PostgreSQL](https://www.google.com/search?q=PostgreSQL)
- [Open Source Software](https://www.google.com/search?q=Open+Source+Software)

## Example Usage
- Select your available equipment and muscle groups you want to train
- Get a workout with suggested exercises and videos
- Save your routine and track progress over time
- Share your workout plans with friends or trainers

> "Users will be able to create routines, save them, and share them with others (even with public links)." — surgomat ([44311247](https://news.ycombinator.com/item?id=44311247))

---

Links:
- **Project GitHub**: [https://github.com/Snouzy/workout-cool](https://github.com/Snouzy/workout-cool)
- **Hacker News Discussion**: [https://news.ycombinator.com/item?id=44309320](https://news.ycombinator.com/item?id=44309320)
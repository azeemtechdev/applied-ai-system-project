# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

My initial UML design centered on a small set of classes that matched the main user actions in PawPal+. I included an `Owner` class to store the pet owner's basic info, preferences, and available time, a `Pet` class to store the animal's profile and care notes, and a `Task` class to represent individual care actions such as feeding, walking, or medication. I also added a `Scheduler` class to make scheduling decisions, a `DayPlan` class to hold the final daily plan, and a `ScheduleItem` class to represent each planned task with its time and reasoning.

Each class had a clear responsibility. `Owner` managed owner preferences and availability, `Pet` stored pet-specific details, and `Task` held the data needed to rank and filter care tasks. `Scheduler` was responsible for generating the plan based on constraints and priorities, `DayPlan` organized the selected tasks into a daily schedule, and `ScheduleItem` kept each scheduled task readable for the UI and explanation output.


**b. Design changes**

Yes, my design changed during implementation. My first version used a simple, flexible structure with tasks, string-based time fields, and a generic constraints dictionary. After I started building the skeleton, I realized that would make conflict checking and scheduling harder to manage, so I refactored the model.

One major change was adding a `TimeWindow` class so preferred times and scheduled times could be handled in a structured way instead of plain text. I also replaced the loose constraints dictionary with a `SchedulingConstraints` class, and I linked `Task` objects to a specific `Pet` so the scheduler can support pet-specific care more clearly. These changes made the design more precise and easier to extend when I start implementing the actual scheduling logic.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

My scheduler uses a lightweight conflict check that warns on overlapping or identical start times instead of solving a full optimization problem. That tradeoff keeps the logic easy to explain and fast to run in a small demo app, but it means the scheduler can miss more subtle scheduling improvements that a more advanced constraint solver would catch.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?

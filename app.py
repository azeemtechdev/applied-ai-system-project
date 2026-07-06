import streamlit as st

from pawpal_system import (
    Owner,
    Pet,
    Task,
    Scheduler,
    SchedulingConstraints,
    DayPlan,
    ScheduleItem,
    TimeWindow,
)

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

# Initialize session state to persist Owner, Pet, and Task objects across reruns
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="", preferences="", available_time_minutes=480, notes="")
    st.session_state.pets = []
    st.session_state.tasks = []

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

st.subheader("Quick Demo Inputs")

# Owner setup (stored in session state) - uses Phase 2 methods
owner_name = st.text_input(
    "Owner name",
    value=st.session_state.owner.name,
    key="owner_name_input"
)
if owner_name != st.session_state.owner.name:
    st.session_state.owner.name = owner_name

owner_prefs = st.text_input(
    "Your preferences",
    value=st.session_state.owner.preferences,
    key="owner_prefs_input",
    help="e.g., 'morning person', 'prefer walks early'"
)
if owner_prefs != st.session_state.owner.preferences:
    st.session_state.owner.update_preferences(owner_prefs)  # Phase 2 method call

available_time = st.number_input(
    "Available time (minutes)",
    min_value=60,
    max_value=1440,
    value=st.session_state.owner.available_time_minutes,
    key="available_time_input"
)
if available_time != st.session_state.owner.available_time_minutes:
    st.session_state.owner.set_available_time(available_time)  # Phase 2 method call

st.markdown("### Pets")
st.caption("Add pet(s) to manage. Each pet gets its own set of care tasks.")

# Display existing pets
if st.session_state.pets:
    st.write(f"**Pets managed ({len(st.session_state.pets)}):**")
    for i, pet in enumerate(st.session_state.pets):
        st.write(f"  • {pet.get_summary()}")

# Add a new pet - uses Phase 2 methods
col1, col2, col3, col4 = st.columns(4)
with col1:
    pet_name = st.text_input("Pet name", value="", key=f"pet_name_{len(st.session_state.pets)}")
with col2:
    species = st.selectbox("Species", ["dog", "cat", "other"], key=f"species_{len(st.session_state.pets)}")
with col3:
    breed = st.text_input("Breed", value="", key=f"breed_{len(st.session_state.pets)}")
with col4:
    age = st.number_input("Age", min_value=1, max_value=30, value=1, key=f"age_{len(st.session_state.pets)}")

if st.button("Add pet"):
    if pet_name:
        new_pet = Pet(name=pet_name, species=species, breed=breed, age=age)
        st.session_state.owner.add_pet(new_pet)  # Phase 2 method call
        st.session_state.pets.append(new_pet)
        st.success(f"✅ Added {pet_name} ({new_pet.get_summary()}) to the plan!")  # Phase 2 method call
        st.rerun()
    else:
        st.warning("Please enter a pet name.")

st.markdown("### Tasks")
st.caption("Add tasks for the selected pet(s). Tasks are ranked by priority when scheduling.")

if not st.session_state.pets:
    st.info("Add at least one pet first to start adding tasks.")
else:
    # Select which pet to add task for
    pet_names = [pet.name for pet in st.session_state.pets]
    selected_pet_name = st.selectbox("Select pet for this task", pet_names)
    selected_pet = next(p for p in st.session_state.pets if p.name == selected_pet_name)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        task_title = st.text_input("Task title", value="Morning walk", key="task_title_input")
    with col2:
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20, key="duration_input")
    with col3:
        priority = st.selectbox("Priority", ["low", "medium", "high"], index=2, key="priority_input")
    
    if st.button("Add task"):
        if task_title:
            new_task = Task(
                title=task_title,
                duration_minutes=int(duration),
                priority=priority,
                category="care",
                pet=selected_pet
            )
            if new_task.is_valid():  # Phase 2 method call
                selected_pet.add_task(new_task)  # Phase 2 method call
                st.session_state.tasks.append(new_task)
                priority_score = new_task.get_priority_score()  # Phase 2 method call
                st.success(f"✅ Added '{task_title}' (priority score: {priority_score}) to {selected_pet.name}'s tasks!")
                st.rerun()
            else:
                st.error("❌ Invalid task (need title and positive duration).")
        else:
            st.warning("⚠️ Please enter a task title.")
    
    # Display tasks by pet with priority scores - uses Phase 2 methods
    st.write("**Tasks by pet (ranked by priority):**")
    for pet in st.session_state.pets:
        if pet.tasks:
            st.write(f"  **{pet.name}:**")
            ranked = sorted(pet.tasks, key=lambda t: (-t.get_priority_score(), t.duration_minutes))
            for task in ranked:
                priority_score = task.get_priority_score()  # Phase 2 method call
                is_valid = task.is_valid()  # Phase 2 method call
                status = "✓" if is_valid else "✗"
                st.write(f"    {status} {task.title} ({task.duration_minutes}m, priority:{task.priority} score:{priority_score})")
        else:
            st.write(f"  **{pet.name}:** No tasks yet")

st.divider()

st.subheader("Generate Daily Schedules")
st.caption("Create optimized schedules for each pet based on available time and priorities.")

if st.button("Generate schedules"):
    if not st.session_state.pets:
        st.warning("Please add at least one pet first.")
    elif not st.session_state.tasks:
        st.warning("Please add at least one task first.")
    else:
        st.success("Generating optimized schedules...")
        
        for pet in st.session_state.pets:
            if pet.tasks:
                constraints = SchedulingConstraints(
                    available_minutes=st.session_state.owner.available_time_minutes,
                    preferred_windows=[],
                    blocked_windows=[],
                    max_tasks=len(pet.tasks)
                )
                
                scheduler = Scheduler(
                    owner=st.session_state.owner,
                    pet=pet,
                    tasks=pet.tasks,
                    constraints=constraints
                )
                
                # Use Phase 2 methods: rank_tasks and check_constraints
                ranked_tasks = scheduler.rank_tasks()
                constraints_met = scheduler.check_constraints()
                
                with st.expander(f"🔍 Task ranking for {pet.name}"):
                    st.write("Tasks ranked by priority (then duration):")
                    for i, task in enumerate(ranked_tasks, 1):
                        st.write(f"  {i}. {task.title} (score: {task.get_priority_score()}, {task.duration_minutes}m)")
                    st.write(f"\n✓ Constraints satisfied: {constraints_met}")
                
                # Generate schedule using Phase 2 methods
                plan = scheduler.generate_schedule()
                
                # Display the plan using explain_plan() from Phase 2
                st.markdown(f"### 📋 Schedule for {pet.name}")
                st.text(plan.explain_plan())
            else:
                st.info(f"ℹ️ {pet.name} has no tasks to schedule yet.")

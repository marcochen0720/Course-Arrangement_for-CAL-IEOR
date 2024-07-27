from pyomo.environ import *
import itertools

# Data Definitions
courses = ['115', '120', '145', '160', '162', '174']
enrollments = {'115': 95, '120': 137, '145': 12, '160': 85, '162': 75, '174': 71}
# courses = ['130', '142A', '150', '171', '172'']
# enrollments = {'130': 50, '142A': 200, '150': 24, '171': 35, '172': 100}
rooms = {'ETCH1174': 45, 'ETCH3107': 45, 'STAN105': 292, 'VLSB2040': 158, 'CORY277': 132}
times = [f"{hour}:00" for hour in range(8, 18)]
prohibited_time = "12:00"  # No classes at this specific time
room_capacity_penalty = 1.0 / 30  # $1 per seat per 30 minutes
early_times = [f"{hour}:00" for hour in range(8, 9)]
early_time_penalty = 10
distance_penalty = 5

# Assumed distances between buildings (matrix)
distances = {
    ('ETCH1174', 'ETCH3107'): 0,
    ('ETCH1174', 'STAN105'): 2,
    ('ETCH1174', 'VLSB2040'): 6,
    ('ETCH1174', 'CORY277'): 1,
    ('ETCH3107', 'STAN105'): 2,
    ('ETCH3107', 'VLSB2040'): 6,
    ('ETCH3107', 'CORY277'): 1,
    ('STAN105', 'VLSB2040'): 4,
    ('STAN105', 'CORY277'): 2,
    ('VLSB2040', 'CORY277'): 4,
}
# Make distances symmetric
for (r1, r2), d in list(distances.items()):
    distances[(r2, r1)] = d

# Model
model = ConcreteModel()

# Indices
model.courses = Set(initialize=courses)
model.rooms = Set(initialize=rooms.keys())
model.times = Set(initialize=times)

# Decision Variables
model.x = Var(model.courses, model.rooms, model.times, within=Binary)

# Define variable y for consecutive course room assignment, assuming it needs different room and time pairs
model.y = Var(model.courses, model.rooms, model.rooms, model.times, model.times, within=Binary)

# Objective Function
def objective_rule(model):
    total_penalty = sum(model.x[c, r, t] * (early_time_penalty if t in early_times else 1) for c in courses for r in rooms for t in times)
    total_penalty += sum(model.x[c, r, t] * room_capacity_penalty * rooms[r] for c in courses for r in rooms for t in times)
    for c in courses:
        for t1, t2 in itertools.permutations(times, 2):
            if abs(int(t1.split(':')[0]) - int(t2.split(':')[0])) == 1:  # Consecutive times
                for (r1, r2), dist in distances.items():
                    total_penalty += model.y[c, r1, r2, t1, t2] * (distance_penalty * dist)
    return total_penalty
model.objective = Objective(rule=objective_rule, sense=minimize)

# Constraints
def room_capacity_rule(model, r, t):
    return sum(model.x[c, r, t] * enrollments[c] for c in courses) <= rooms[r]
model.room_capacity = Constraint(model.rooms, model.times, rule=room_capacity_rule)

def course_schedule_rule(model, c):
    return sum(model.x[c, r, t] for r in rooms for t in times) == 1  # Each course once a week
model.course_schedule = Constraint(model.courses, rule=course_schedule_rule)

def no_overlap_rule(model, r, t):
    return sum(model.x[c, r, t] for c in courses) <= 1
model.no_overlap = Constraint(model.rooms, model.times, rule=no_overlap_rule)

def consecutive_assignment_rule(model, c, r1, r2, t1, t2):
    return model.y[c, r1, r2, t1, t2] <= model.x[c, r1, t1]
    return model.y[c, r1, r2, t1, t2] <= model.x[c, r2, t2]
    return model.y[c, r1, r2, t1, t2] >= model.x[c, r1, t1] + model.x[c, r2, t2] - 1
model.consecutive_assignment = Constraint(model.courses, model.rooms, model.rooms, model.times, model.times, rule=consecutive_assignment_rule)

# Solver configuration
solver = SolverFactory('cbc')
result = solver.solve(model, tee=True)

# Display results
for c in courses:
    for r in rooms:
        for t in times:
            if model.x[c, r, t].value == 1:
                print(f"Course {c} is scheduled in room {r} at time {t}")

class Exercise:
    def __init__(self, name, description, muscle_group):
        self.name = name
        self.description = description
        self.muscle_group = muscle_group


class Meal:
    def __init__(self, name, calories, nutrients):
        self.name = name
        self.calories = calories
        self.nutrients = nutrients


class Workout:
    def __init__(self, name, exercises, duration):
        self.name = name
        self.exercises = exercises
        self.duration = duration

class RunCounter:
    def __init__(self):
        """Initialize the run counter."""
        self.run = 1  # Start from 1

    def function_a(self):
        """Example function A."""
        print(f"Run {self.run}: Executing function_a()")

    def function_b(self):
        """Example function B."""
        print(f"Run {self.run}: Executing function_b()")

    def function_c(self):
        """Example function C."""
        print(f"Run {self.run}: Executing function_c()")

    def execute_series(self):
        """
        Executes a series of functions, then increments the run counter.
        """
        print(f"🏃‍♂️ Starting Run {self.run}")
        
        # Call your functions in order
        self.function_a()
        self.function_b()
        self.function_c()
        
        # Increment run after completing the series
        self.run += 1
        print(f"✅ Run {self.run - 1} Completed! Moving to Run {self.run}.\n")

# Example usage:
counter = RunCounter()

# Run the series 3 times
for _ in range(3):
    counter.execute_series()
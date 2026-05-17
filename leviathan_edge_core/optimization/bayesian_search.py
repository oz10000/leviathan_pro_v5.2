from skopt import gp_minimize

class BayesianOptimizer:
    def optimize(self, objective_func, space, n_calls=50):
        result = gp_minimize(objective_func, space, n_calls=n_calls, random_state=42)
        return result.x, -result.fun

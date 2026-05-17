import random

class GeneticOptimizer:
    def __init__(self, param_ranges, pop_size=50, generations=20):
        self.ranges = param_ranges
        self.pop = [{k: random.uniform(v[0], v[1]) for k, v in param_ranges.items()} for _ in range(pop_size)]
        self.generations = generations
        self.pop_size = pop_size

    def evolve(self, fitness_func):
        for gen in range(self.generations):
            scored = [(ind, fitness_func(ind)) for ind in self.pop]
            scored.sort(key=lambda x: x[1], reverse=True)
            self.pop = [ind for ind, _ in scored[:self.pop_size // 2]]
            while len(self.pop) < self.pop_size:
                parent1, parent2 = random.sample(self.pop[:self.pop_size // 4], 2)
                child = {}
                for k in self.ranges:
                    if random.random() < 0.5:
                        child[k] = parent1[k]
                    else:
                        child[k] = parent2[k]
                    if random.random() < 0.1:
                        child[k] = random.uniform(self.ranges[k][0], self.ranges[k][1])
                self.pop.append(child)
        return scored[0][0]

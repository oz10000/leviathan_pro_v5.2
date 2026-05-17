import pandas as pd

class RobustnessSurface:
    def compute(self, param1_name, param1_vals, param2_name, param2_vals, func):
        results = []
        for v1 in param1_vals:
            for v2 in param2_vals:
                score = func({param1_name: v1, param2_name: v2})
                results.append((v1, v2, score))
        df = pd.DataFrame(results, columns=[param1_name, param2_name, 'score'])
        return df.pivot(index=param1_name, columns=param2_name, values='score')

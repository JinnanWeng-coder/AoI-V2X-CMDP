import random
class AoIModel:
    def __init__(self, n_platoons, dt_ms=1.0, max_aoi_ms=100.0, init_aoi_ms=None):
        self.n_platoons = n_platoons
        self.dt_ms = dt_ms
        self.max_aoi_ms = max_aoi_ms
        self.aoi = [init_aoi_ms if init_aoi_ms is not None else max_aoi_ms] * n_platoons

    def reset(self, value_ms=None):
        val = self.max_aoi_ms if value_ms is None else value_ms
        self.aoi = [val] * self.n_platoons

    def step(self, success_flags):
        """
        success_flags: 长度为 n_platoons 的布尔列表
        True  -> 本时隙成功更新到 RSU, AoI 重置为 dt_ms
        False -> 本时隙未成功更新, AoI += dt_ms
        """
        next_aoi = []
        for i in range(self.n_platoons):
            if success_flags[i]:
                next_aoi.append(self.dt_ms)
            else:
                next_aoi.append(min(self.aoi[i] + self.dt_ms, self.max_aoi_ms))
        self.aoi = next_aoi
        return self.aoi
    
model = AoIModel(n_platoons=3, dt_ms=1.0, max_aoi_ms=100.0, init_aoi_ms=20.0)

for t in range(10):
    success = [random.random() < 0.8,
               random.random() < 0.2,
               random.random() < 0.5]
    print(f"slot {t}, success={success}, before={model.aoi}")
    model.step(success)
    print(f"slot {t}, after ={model.aoi}")
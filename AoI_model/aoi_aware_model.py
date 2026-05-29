class AoIFromV2I:
    def __init__(self, n_platoons, dt_ms=1.0, max_aoi_ms=100.0, c_min=1.0):
        self.n_platoons = n_platoons
        self.dt_ms = dt_ms
        self.max_aoi_ms = max_aoi_ms
        self.c_min = c_min
        self.aoi = [max_aoi_ms] * n_platoons

    def reset(self, value_ms=None):
        val = self.max_aoi_ms if value_ms is None else value_ms
        self.aoi = [val] * self.n_platoons

    def is_successful_v2i(self, mode, v2i_rate):
        """
        mode = 0 表示当前时隙用于 V2I
        mode = 1 表示当前时隙用于 V2V
        """
        return (mode == 0) and (v2i_rate >= self.c_min)

    def step(self, modes, v2i_rates):
        next_aoi = []
        success_flags = []

        for i in range(self.n_platoons):
            success = self.is_successful_v2i(modes[i], v2i_rates[i])
            success_flags.append(success)

            if success:
                next_aoi.append(self.dt_ms)
            else:
                next_aoi.append(min(self.aoi[i] + self.dt_ms, self.max_aoi_ms))

        self.aoi = next_aoi
        return self.aoi, success_flags
    
model = AoIFromV2I(n_platoons=2, dt_ms=1.0, max_aoi_ms=100.0, c_min=3.0)

modes_seq = [
    [0, 1],
    [0, 0],
    [1, 0],
    [0, 0],
]

rates_seq = [
    [4.2, 0.0],
    [2.5, 3.8],
    [0.0, 2.0],
    [5.1, 4.0],
]

for t, (modes, rates) in enumerate(zip(modes_seq, rates_seq)):
    aoi, success = model.step(modes, rates)
    print(f"t={t}, success={success}, aoi={aoi}")
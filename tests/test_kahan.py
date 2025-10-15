from lib.kahan import KahanSum
def test_kahan_sum():
    ks = KahanSum()
    for _ in range(100000):
        ks.add(0.00001)
    assert abs(ks.value() - 1.0) < 1e-6

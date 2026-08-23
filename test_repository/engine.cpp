#include <iostream>
#include <vector>
#include "engine.hpp"

int calculateFactorial(int n) {
    if (n <= 1) return 1;
    return n * calculateFactorial(n - 1);
}

class Vector3D {
public:
    Vector3D(double x, double y, double z) : x(x), y(y), z(z) {}
    double magnitude() const {
        return x * x + y * y + z * z;
    }
private:
    double x, y, z;
};

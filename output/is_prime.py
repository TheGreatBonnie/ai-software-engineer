import math


def is_prime(n: int) -> bool:
    """Check if a number is prime using optimized trial division.

    Optimizations:
    1. Handle small cases and even numbers immediately.
    2. Only check odd divisors up to sqrt(n).
    3. Skip multiples of 2 and 3 using 6k±1 wheel.
    """
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False

    # All primes > 3 are of the form 6k ± 1.
    # Check divisors of the form 6k - 1 and 6k + 1 up to sqrt(n).
    limit = math.isqrt(n)
    i = 5
    while i <= limit:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6

    return True


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <number>")
        sys.exit(1)

    try:
        num = int(sys.argv[1])
    except ValueError:
        print("Error: argument must be an integer.")
        sys.exit(1)

    if is_prime(num):
        print(f"{num} is prime.")
    else:
        print(f"{num} is not prime.")

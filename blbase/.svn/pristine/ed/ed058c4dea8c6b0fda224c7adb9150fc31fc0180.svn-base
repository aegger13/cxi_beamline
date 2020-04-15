from __future__ import print_function
import random

class LaserSequence(object):
    """
    Class with macros for setting up the laser sequence.

    Parameters
    ----------
    sequencer : blbase.eventsequencer.EventSequencer
        event sequencer object to use as the laser sequence

    on_code : int
        event code that turns the laser on

    off_code : int
        event code that turns the laser off
    """
    def __init__(self, sequencer, on_code, off_code):
        self.event = sequencer
        self.on_code = on_code
        self.off_code = off_code
        self.comment_map = {on_code : "laser on", off_code : "laser off"}

    def random_on_off(self, n_total, n_on, force_prime=True):
        """
        Create a random sequence of on and off shots for the laser sequence.

        Parameters
        ----------
        n_total : int
            The total number of events in one iteration of the sequence.
            This needs to be a prime number if force_prime=True.

        n_on :
            number of shots where the laser is on

        force_prime : bool, optional
            if True, requires you to pick n_total as a prime number
        """
        if not isinstance(n_total, int) or not isinstance(n_on, int):
            print("Expected int arguments for n_total, n_on")
        elif n_total <= n_on:
            print("Expected n_total > n_on")
        elif force_prime and not is_prime(n_total):
            print("You must pick a prime number of sequence steps!")
            print("Here are some primes for you:")
            primes = get_primes(100)
            print(primes)
        elif n_total > self.event.maxEventCount:
            print("More events than max sequence size! ({})".format(self.event.maxEventCount))
        else:
            seq = n_on * [self.on_code] + (n_total - n_on) * [self.off_code]
            random.shuffle(seq)
            for i, code in enumerate(seq):
                self.event.setstep(i, code, 1, 0, comment=self.comment_map[code])
            self.event.update()
            self.event.setnsteps(n_total)

def is_prime(n, valid_divisors=None):
    """
    Check prime using divisors, which is sufficient for small primes.

    Parameters
    ----------
    n : int
        number to check

    valid_divisors : list, optional
        if provided, we'll only use elements in this list as the divisors

    Returns
    -------
    ok : bool
        True if n is prime.
    """
    if n < 4:
        return True
    if valid_divisors is None:
        return all(n % i != 0 for i in range(2, n))
    else:
        return all(n % i != 0 for i in range(2, n) if i in valid_divisors)

def get_primes(n):
    """
    Get the first n prime numbers.

    Parameters
    ----------
    n : int
        number of primes to generate

    Returns
    -------
    primes: list
        list of the first n prime numbers
    """
    primes = []
    i = 2
    while len(primes) < n:
        if is_prime(i, primes):
            primes.append(i)
        i+=1
    return primes

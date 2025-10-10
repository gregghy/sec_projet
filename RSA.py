from random import randint, randrange
import hashlib

class RSA():
	def __init__(self, bits: int = 1024) -> None:
		self.public, self.private = self.genKeypair(bits)

	# Miller-Rabin https://fr.wikipedia.org/wiki/Test_de_primalit%C3%A9_de_Miller-Rabin
	# (slightly modified) implementation taken from https://rosettacode.org/wiki/Miller%E2%80%93Rabin_primality_test#Python:_Probably_correct_answers
	def isPrime(self, n: int) -> bool:
		"""
		Miller-Rabin primality test.

		A return value of False means n is certainly not prime. A return value of
		True means n is very likely a prime.
		"""

		checks = [2, 3, 5, 7, 11, 13, 17, 19, 23]
		trials = 8

		def trial_composite(a) -> bool:
			if pow(a, d, n) == 1:
				return False
			for i in range(s):
				if pow(a, 2 ** i * d, n) == n - 1:
					return False
			return True

		# Miller-Rabin test for primes
		if n in checks:
			return True
		elif n < checks[-1]:
			return False

		s = 0
		d = n - 1
		while d % 2 == 0:
			d >>= 1
			s += 1
		assert(2 ** s * d == n - 1)
	
		for _ in range(trials):
			a = randrange(2, n)
			if trial_composite(a):
				return False
		return True

	# generate random prime number between a and b
	def randomPrime(self, a: int, b: int) -> int:
		p = randint(a, b)
		while not self.isPrime(p):
			# according to https://en.wikipedia.org/wiki/Prime_number_theorem
			# this loop has a p/log(p) chance of being escaped every iteration
			# significantly faster than using a seive of arithosthenes like I was earlier
			p = randint(a, b)
		return p

	# generate random prime number of binary length (bits)
	def getPrime(self, bits: int = 1024) -> int:
		return self.randomPrime(2**(bits-1), 2**bits - 1)

	# modular inverse of number a in base b
	def modInverse(self, a: int, b: int) -> int:
		return pow(a, -1, b)

	# generate public and private (in that order) RSA keypair of a given length.
	# automatically called upon RSA object initialisation
	# recommend 1024 bits or more
	# usage: () or (number of bits)
	def genKeypair(self, bits: int = 1024) -> tuple[tuple[int, int], tuple[int, int]]:
		p, q = self.getPrime(bits), self.getPrime(bits)
		while p == q:
			p, q = self.getPrime(bits), self.getPrime(bits)
		
		n = p * q
		phin = (p - 1) * (q - 1)
		e = 65537
		orig_e = e
		while phin % e == 0:
			e = self.randomPrime(orig_e, orig_e * 2)
		
		d = self.modInverse(e, phin)
		return ((e,n), (d,n))

	# returns public key of RSA object
	# usage: ()
	def getPublicKey(self) -> tuple[int, int]:
		return self.public

	# encrypt RSA
	# usage: (receiver's public key, message)
	def enc(self, pub: tuple[int, int], s: str) -> tuple[int, int]:
		r_pub_e, r_n = pub
		m_int = int.from_bytes(s.encode('utf-8'), 'big')
		signed = self.sign(m_int)
		cipher = pow(m_int, r_pub_e, r_n)
		return (cipher, signed[1])

	# decrypt RSA
	# usage: receiver.dec(sender's public key, encrypted message)
	def dec(self, pub, enc_s: tuple[int, int]) -> str:
		priv_d, n = self.private
		m_int = pow(enc_s[0], priv_d, n)
		us = int.to_bytes(m_int, (m_int.bit_length() + 7) // 8, 'big').decode('utf-8')
		v = self.verify(pub, (m_int, enc_s[1]))
		assert(v)
		return us

	# sign message (pre_encryption)
	# usage: (message to sign)
	def sign(self, s: int) -> tuple[int, int]:
		priv_d, n = self.private
		s_bytes = int.to_bytes(s, (s.bit_length() + 7) // 8, 'big')
		hash_int = int.from_bytes(hashlib.sha256(s_bytes).digest(), 'big')
		m = pow(hash_int, priv_d, n)
		return (s, m)

	# verify signature (post-decryption)
	# usage: (public key, signed message)
	def verify(self, pub: tuple[int, int], s_ss: tuple[int, int]) -> bool:
		pub_e, n = pub
		s_bytes = int.to_bytes(s_ss[0], (s_ss[0].bit_length() + 7) // 8, 'big')
		hash_int = int.from_bytes(hashlib.sha256(s_bytes).digest(), 'big')
		m = pow(s_ss[1], pub_e, n)
		return m == hash_int

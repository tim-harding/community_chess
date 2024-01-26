import unittest
from chessbot import database


class TestDatabase(unittest.TestCase):
    def setUp(self) -> None:
        database.open_db("test.db", reset=True)


if __name__ == "__main__":
    unittest.main()

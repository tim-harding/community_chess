import chess


def extract_move(board: chess.Board, comment: str):
    for word in comment.replace(".", "").split():
        try:
            return board.parse_san(word)
        except ValueError as e:
            print(e)
            pass

        try:
            return board.parse_uci(word)
        except ValueError as e:
            print(e)
            pass

    return None


def basic_comment_test():
    comment = "I think we should play e4."
    board = chess.Board()
    move = extract_move(board, comment)
    print(move)


def ambiguous_move_test():
    board = chess.Board()
    moves = [
        "Nc3",
        "a6",
        "Ne4",
        "b6",
        "Nf3",
        "c6",
    ]
    for move in moves:
        board.push_san(move)
    comment = "Ng5"
    move = extract_move(board, comment)
    print(move)


def straight_up_illegal():
    board = chess.Board()
    comment = "Nc4"
    move = extract_move(board, comment)
    print(move)


if __name__ == "__main__":
    # basic_comment_test()
    # ambiguous_move_test()
    straight_up_illegal()

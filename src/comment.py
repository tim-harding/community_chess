import chess


def extract_move(board: chess.Board, comment: str):
    for word in comment.split():
        try:
            return board.parse_san(word)
        except ValueError:
            pass

        try:
            return board.parse_uci(word)
        except ValueError:
            pass

    return None


if __name__ == "__main__":
    comment = "I think we should play e4"
    board = chess.Board()
    move = extract_move(board, comment)
    print(move)

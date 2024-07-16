from src.tile import Tile
from src.session import Session
from src.side_type import SideType
from src.tile_evaluation import TileEvaluation
from src.tile_evaluation_factory import TileEvaluationFactory

def test_rated_tile_eq():
    session = Session()
    session.load_from_csv("./tests/data/perspective_group_extensions.csv", simulate_tile_placement=False)

    candidate_tiles = session.compute_candidate_tiles(
        [SideType.PONDS, SideType.PONDS, SideType.CROPS, SideType.TRAIN, SideType.PONDS, SideType.PONDS],
        SideType.PONDS)

    tile_evaluation = TileEvaluationFactory.create(candidate_tiles, session)

    for i in range(len(tile_evaluation.rating_details)):
        if i > 0:
            assert TileEvaluation.RatedTile(tile_evaluation.rating_details[i]) !=\
                   TileEvaluation.RatedTile(tile_evaluation.rating_details[i-1])

        assert TileEvaluation.RatedTile(tile_evaluation.rating_details[i]) ==\
               TileEvaluation.RatedTile(tile_evaluation.rating_details[i])
        assert TileEvaluation.RatedTile(tile_evaluation.rating_details[i]) != "str"
        assert TileEvaluation.RatedTile(tile_evaluation.rating_details[i]) != SideType.CROPS

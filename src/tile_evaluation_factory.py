from src.tile_evaluation import TileEvaluation

class TileEvaluationFactory:
    @staticmethod
    def create(candidate_tiles, session):
        open_tiles_per_coordinates = {}
        open_tiles_per_candidate = []
        if candidate_tiles is not None:
            for candidate in candidate_tiles:
                if candidate.coordinates not in open_tiles_per_coordinates:
                    open_tiles_per_coordinates[candidate.coordinates] = \
                        session.compute_open_coords_for_tile(candidate)
                open_tiles_per_candidate.append(open_tiles_per_coordinates[candidate.coordinates])

        return TileEvaluation(candidate_tiles, open_tiles_per_candidate,
                              session.played_tiles, session.groups)

from . import *


def GetAbilities() -> Sequence['Ability']:
    def serve(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        main_scheme = Worlds.FindMainScheme(effect)
        if main_scheme:
            effect.this.PlaceThreatOnSchemes([main_scheme], 2, effect)

    return [
        CommandObligationAbility(
            'Exhaust "Serve." and remove 1 command counter → place 2 threat on the main scheme',
            serve,
        ),
        PurpleManBoostAbility(),
    ]

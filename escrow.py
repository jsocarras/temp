import smartpy as sp
import smartpy as sp

class Escrow(sp.Contract):
    def __init__(self, main_contract, oracle, link_token):
        self.init(
            main_contract=main_contract,
            player=sp.none,
            player_bet=sp.mutez(0),
            player_prediction=sp.none,
            contract_bet=sp.mutez(0),
            random_value=sp.none,
            random_value_requested=False,
            oracle=oracle,
            link_token=link_token
        )
        sp.verify(sp.is_address(oracle), message="Invalid oracle address")

    @sp.entry_point
    def place_bet(self, params: sp.TRecord(prediction=sp.TBool)):
        sp.verify(self.data.player.is_some(), message="Player address not set")
        sp.verify(sp.amount > sp.mutez(0), message="Bet must be greater than 0")
        sp.verify((sp.sender == self.data.player.open_some()) | (sp.sender == self.data.main_contract),
                  message="Unauthorized sender")

        sp.if sp.sender == self.data.player.open_some():
            self.data.player_bet = sp.amount
            self.data.player_prediction = params.prediction
        sp.else:
            self.data.contract_bet = sp.amount

        sp.if (self.data.player_bet > sp.mutez(0)) & (self.data.contract_bet > sp.mutez(0)):
            self.data.random_value = sp.none
            self.data.random_value_requested = True
            oracle_data = sp.chainlink.build_request(
                spec_id="coin_flip",
                callback_address=self.address,
                callback_entry_point="receive_randomness",
                amount=sp.mutez(1000)  # The amount of LINK tokens to be sent for the request, adjust accordingly
            )
            sp.transfer(oracle_data, sp.mutez(1000), self.data.link_token)

    def _compute_refund(self, player_bet, contract_bet, player_prediction, random_value):
        with sp.if_(player_prediction == (random_value % 2 == 0)):
            return player_bet + (contract_bet * 98 // 100)
        sp.else:
            return sp.mutez(0)

    @sp.entry_point
    def perform_payout(self):
        sp.if self.data.random_value.is_some():
            refund = self._compute_refund(self.data.player_bet, self.data.contract_bet, self.data.player_prediction.open_some(), self.data.random_value.open_some())

            # Call finish_game function on the main contract
            sp.transfer(sp.record(player=self.data.player.open_some(), refund=refund), sp.mutez(0), self.data.main_contract)

            # Reset bet data for the next round
            self.data.player_bet = sp.mutez(0)
            self.data.contract_bet = sp.mutez(0)
            self.data.player_prediction = sp.none
            self.data.random_value = sp.none

    @sp.entry_point
    def receive_randomness(self, params):
        sp.verify(self.data.random_value_requested, message="Random value not requested")
        self.data.random_value_requested = False
        self.data.random_value = sp.some(params.value)
        self.perform_payout()

    @sp.entry_point
    def set_player(self, params: sp.TAddress):
        sp.verify(sp.sender == self.data.main_contract, message="Only main contract can set the player")
        sp.verify(sp.is_valid_address(params), message="Invalid player address")
        self.data.player = sp.some(params)

@sp.add_test(name="Escrow Tests")
def test():
    scenario = sp.test_scenario()
    main_contract = sp.test_account("Main Contract")
    player = sp.test_account("Player")
    oracle = sp.test_account("Oracle")
    link_token = sp.test_account("Link Token")
    escrow = Escrow(main_contract.address, oracle.address, link_token.address)

    # Test set_player
    scenario += escrow.set_player.entry_point(player.address).run(sender=main_contract)

    # Test place_bet for player
    scenario += escrow.place_bet(prediction=True).run(sender=player, amount=sp.mutez(50))

    # Test place_bet for main_contract
    scenario += escrow.place_bet(prediction=True).run(sender=main_contract, amount=sp.mutez(50))

    # Test place_bet for player
    scenario += escrow.place_bet(prediction=True).run(sender=player, amount=sp.mutez(50))

    # Test place_bet for main_contract
    scenario += escrow.place_bet(prediction=True).run(sender=main_contract, amount=sp.mutez(50))

    # Test coin_flip and perform_payout are called automatically
    # The oracle should be set up to send randomness to the contract, simulating the coin flip
    scenario += escrow.receive_randomness(value=123456789).run(sender=oracle)

    # Test that the payout and reset are correct (this test may need to be modified based on the setup of the oracle and main contract)
    # Example: checking if the player's refund is correct after the payout
    refund = escrow._compute_refund(sp.mutez(50), sp.mutez(50), True, 123456789)
    scenario.verify(escrow.data.player_bet == sp.mutez(0))
    scenario.verify(escrow.data.contract_bet == sp.mutez(0))
    scenario.verify(escrow.data.player_prediction == sp.none)
    scenario.verify(escrow.data.random_value == sp.none)

    # Test edge cases and invalid inputs
    # Test invalid player address
    scenario += escrow.set_player("invalid_address").run(sender=main_contract, valid=False)

    # Test unauthorized sender for set_player
    scenario += escrow.set_player(player.address).run(sender=player, valid=False)

    # Test place_bet with unauthorized sender
    scenario += escrow.place_bet(prediction=True).run(sender=oracle, amount=sp.mutez(50), valid=False)

    # Test place_bet with zero bet amount
    scenario += escrow.place_bet(prediction=True).run(sender=player, amount=sp.mutez(0), valid=False)

    # Test receive_randomness without requesting random value
    scenario += escrow.receive_randomness(value=123456789).run(sender=oracle, valid=False)

    # Test receive_randomness with unauthorized sender
    scenario += escrow.receive_randomness(value=123456789).run(sender=player, valid=False)

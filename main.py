import smartpy as sp
# import smartpy.chainlink as chainlink

class CoinFlip(sp.Contract):
    def __init__(self, owner, oracle, link_token):
        self.init(
            players=sp.big_map(tkey=sp.TAddress, tvalue=sp.TMutez),
            escrow=sp.none,
            owner=owner,
            oracle=oracle,
            link_token=link_token,
            total_players_balance=sp.mutez(0)
        )

    DepositParams = sp.TRecord(amount=sp.TMutez)
    WithdrawParams = sp.TRecord(amount=sp.TMutez)
    SetEscrowParams = sp.TRecord(escrow=sp.TAddress)
    BetParams = sp.TRecord(amount=sp.TMutez, prediction=sp.TBool)
    OwnerWithdrawParams = sp.TRecord(destination=sp.TAddress, amount=sp.TMutez)
    FinishGameParams = sp.TRecord(player=sp.TAddress, refund=sp.TMutez)

    @sp.entry_point
    def add_player(self, params: sp.TRecord(address=sp.TAddress, amount=sp.TMutez)):
        self.data.players[params.address] = params.amount
        self.data.total_players_balance += params.amount

    # Deposit function
    @sp.entry_point
    def deposit(self):
        sp.verify(sp.amount > sp.mutez(0), message="Deposit must be greater than 0")
        sp.if self.data.players.contains(sp.sender):
            self.data.players[sp.sender] += sp.amount
            self.data.total_players_balance += sp.amount
        sp.else:
            self.data.players[sp.sender] = sp.amount
            self.data.total_players_balance += sp.amount

    # Withdraw function
    @sp.entry_point
    def withdraw(self):
        sp.verify(self.data.players.contains(sp.sender), message="Sender not registered")
        sp.verify(self.data.players[sp.sender] > sp.mutez(0), message="Insufficient balance")
        amount = self.data.players[sp.sender]
        self.data.players[sp.sender] = sp.mutez(0)
        self.data.total_players_balance -= amount
        sp.send(sp.sender, amount)


    # Set escrow address
    @sp.entry_point
    def set_escrow(self, params: sp.TAddress):
        sp.verify(sp.sender == self.data.owner, message="Only admin can set the escrow")
        escrow_contract = sp.contract(
            sp.TRecord(amount=sp.TMutez, player=sp.TAddress, prediction=sp.TBool),
            params,
            entry_point="entry_point_name"  # Replace with the correct entry point name of the escrow contract
        )
        sp.verify(escrow_contract.is_some(), message="Invalid escrow contract")
        self.data.escrow = escrow_contract


    # Set oracle address
    @sp.entry_point
    def set_oracle(self, params: sp.TAddress):
        sp.verify(sp.sender == self.data.owner, message="Only admin can set the oracle")
        self.data.oracle = params

    # Bet function
    @sp.entry_point
    def bet(self, params: sp.TRecord(amount=sp.TMutez, prediction=sp.TBool, contract_balance=sp.TMutez)):
        sp.verify(self.data.players.contains(sp.sender), message="Sender not registered")
        sp.verify(self.data.players[sp.sender] >= params.amount, message="Insufficient balance")
        max_bet = sp.utils.nat_to_mutez(sp.as_nat(params.contract_balance) // 50) # 2% of the contract balance
        sp.verify(params.amount <= max_bet, message="Bet amount exceeds maximum allowed")
        sp.verify(self.data.escrow.is_some(), message="Escrow not set")
        self.data.players[sp.sender] -= params.amount
        self.data.total_players_balance -= params.amount

        # Call escrow contract to place the bet
        sp.transfer(sp.record(player=sp.sender, amount=params.amount, prediction=params.prediction), sp.mutez(0), self.data.escrow.open_some())

    @sp.entry_point
    def owner_withdraw(self, params: sp.TRecord(destination=sp.TAddress, amount=sp.TMutez)):
        sp.verify(sp.sender == self.data.owner, message="Only owner can withdraw")
        sp.verify(params.amount > sp.mutez(0), message="Withdraw amount must be greater than 0")

        # Check if the contract has enough balance
        sp.verify(sp.balance >= params.amount + self.data.total_players_balance, message="Insufficient contract balance")

        # Withdraw the specified amount from the contract balance
        sp.send(params.destination, params.amount)

    # @sp.view(sp.TMutez)
    # @sp.view()
    # @sp.entry_point
    # def get_balance(self, params: sp.TAddress) -> sp.TMutez:
    #     sp.result(sp.balance)
    # @sp.view
    # def get_balance(self, params: sp.TAddress) -> sp.TMutez:
    #     sp.if self.data.players.contains(params):
    #         sp.result(self.data.players[params])
    #     sp.else:
    #         sp.result(sp.mutez(0))

    # @sp.view(sp.TMutez)
    # def get_balance(self, params: sp.TAddress) -> sp.TMutez:
    #     sp.if self.data.players.contains(params):
    #         sp.result(self.data.players[params])
    #     sp.else:
    #         sp.result(sp.mutez(0))

    # @sp.view()
    # def get_balance(self, params: sp.TAddress) -> sp.TMutez:
    #     sp.if self.data.players.contains(params):
    #         sp.result(self.data.players[params])
    #     sp.else:
    #         sp.result(sp.mutez(0))

    # @sp.view(sp.TMutez)
    # def get_balance(self, params: sp.TAddress) -> sp.TMutez:
    #     sp.if self.data.players.contains(params):
    #         sp.result(self.data.players[params])
    #     sp.else:
    #         sp.result(sp.mutez(0))

    # @sp.entry_point
    # @sp.view
    # def get_balance(self, params: sp.TAddress) -> sp.TMutez:
    #     sp.if self.data.players.contains(params):
    #         return self.data.players[params]
    #     sp.else:
    #         return sp.mutez(0)

    # @sp.view
    # def get_balance(self, params: sp.TAddress) -> sp.TMutez:
    #     sp.if self.data.players.contains(params):
    #         return self.data.players[params]
    #     sp.else:
    #         return sp.mutez(0)

    @sp.utils.view(sp.TMutez)
    def get_balance(self, params):
        sp.set_type(params, sp.TAddress)
        sp.if self.data.players.contains(params):
            sp.result(self.data.players[params])
        sp.else:
            sp.result(sp.mutez(0))



    #
    # @sp.view(sp.TMutez)
    # def get_contract_balance(self):
    #     return sp.balance

    # Finish game function
    @sp.entry_point
    def finish_game(self, params: sp.TRecord(player=sp.TAddress, refund=sp.TMutez)):
        sp.verify(sp.sender == self.data.oracle, message="Only oracle can finish the game")
        sp.verify(self.data.players.contains(params.player), message="Player not found")
        self.data.players[params.player] += params.refund
        self.data.total_players_balance += params.refund

@sp.add_test(name="CoinFlip Tests")
def test():
    scenario = sp.test_scenario()
    owner = sp.test_account("Owner")
    player = sp.test_account("Player")
    player2 = sp.test_account("Player2")
    oracle = sp.test_account("Oracle")
    link_token = sp.test_account("Link Token")
    main_contract = CoinFlip(owner.address, oracle.address, link_token.address)
    scenario += main_contract

    # Test deposit
    scenario += main_contract.deposit().run(sender=player, amount=sp.mutez(1000))
    scenario.verify(main_contract.data.players[player.address] == sp.mutez(1000))

    # Test deposit for a second player
    scenario += main_contract.deposit().run(sender=player2, amount=sp.mutez(2000))
    scenario.verify(main_contract.data.players[player2.address] == sp.mutez(2000))

    # Test withdraw
    scenario += main_contract.withdraw().run(sender=player)
    scenario.verify(main_contract.data.players[player.address] == sp.mutez(0))

    # Test owner withdraw with sufficient contract balance
    # scenario += main_contract.owner_withdraw(destination=owner, amount=sp.mutez(100)).run(sender=owner, valid=False)
    # scenario += main_contract.owner_withdraw(destination=owner, amount=sp.mutez(100), contract_address=main_contract.address).run(sender=owner, valid=False)
    # scenario += main_contract.owner_withdraw(destination=owner.address, amount=sp.mutez(100), contract_address=main_contract.address).run(sender=owner, valid=False)
    scenario += main_contract.owner_withdraw(destination=owner.address, amount=sp.mutez(100)).run(sender=owner, valid=False)

    # Test setting escrow
    escrow_account = sp.test_account("Escrow")
    scenario += main_contract.set_escrow(escrow_account.address).run(sender=owner)

    # Test bet
    # scenario += main_contract.bet(amount=sp.mutez(10), prediction=True).run(sender=player, valid=False)  # Player has insufficient balance
    # scenario += main_contract.bet(amount=sp.mutez(10), prediction=True, contract_balance=scenario.compute_balance(main_contract)).run(sender=player, valid=False)  # Player has insufficient balance
    # scenario += main_contract.bet(amount=sp.mutez(10), prediction=True, contract_balance=sp.balance(main_contract.address)).run(sender=player, valid=False)  # Player has insufficient balance
    # scenario += main_contract.bet(amount=sp.mutez(10), prediction=True, contract_balance=main_contract.get_balance()).run(sender=player, valid=False)  # Player has insufficient balance
    # scenario += main_contract.bet(amount=sp.mutez(10), prediction=True, contract_balance=main_contract.get_balance(main_contract.address)).run(sender=player, valid=False)  # Player has insufficient balance
    # contract_balance = main_contract.get_balance(sp.record(address=main_contract.address)).open_some()
    # contract_balance = scenario.compute_view(main_contract.get_balance, main_contract.address)
    contract_balance = scenario.compute_view(main_contract.get_balance, main_contract, main_contract.address)
    # player_balance = scenario.compute_view(main_contract.get_balance, player.address)
    # player_balance = scenario.get_view(main_contract.get_balance, player.address)
    # scenario += main_contract.bet(amount=sp.mutez(10), prediction=True, contract_balance=contract_balance).run(sender=player, valid=False)  # Player has insufficient balance
    scenario += main_contract.bet(amount=sp.mutez(10), prediction=True, contract_balance=player_balance).run(sender=player)  # Player has insufficient balance
    scenario += main_contract.deposit().run(sender=player, amount=sp.mutez(1000))
    # scenario += main_contract.bet(amount=sp.mutez(10), prediction=True).run(sender=player)
    # scenario += main_contract.bet(amount=sp.mutez(10), prediction=True, contract_balance=scenario.compute_balance(main_contract)).run(sender=player)
    # scenario += main_contract.bet(amount=sp.mutez(10), prediction=True, contract_balance=main_contract.get_balance()).run(sender=player)
    # contract_balance = scenario.compute_view(main_contract.get_balance, main_contract.address)
    # contract_balance = scenario.compute_view(main_contract.get_balance, main_contract, main_contract.address)
    # player_balance = scenario.compute_view(main_contract.get_balance, player.address)
    # scenario += main_contract.bet(amount=sp.mutez(10), prediction=True, contract_balance=sp.balance(main_contract.address)).run(sender=player)
    # scenario += main_contract.bet(amount=sp.mutez(10), prediction=True, contract_balance=contract_balance).run(sender=player)
    scenario += main_contract.bet(amount=sp.mutez(10), prediction=True, contract_balance=player_balance).run(sender=player)

    scenario.verify(main_contract.data.players[player.address] == sp.mutez(990))

    # Test bet exceeding maximum allowed
    # scenario += main_contract.bet(sp.record(amount=sp.mutez(50000), prediction=True, contract_balance=scenario.compute_balance(main_contract)))
    # scenario += main_contract.bet(sp.record(amount=sp.mutez(50000), prediction=True, contract_balance=scenario.compute_balance(main_contract))).run(sender=player, valid=False)
    # scenario += main_contract.bet(sp.record(amount=sp.mutez(50000), prediction=True, contract_balance=main_contract.get_balance()).run(sender=player, valid=False))
    # scenario += main_contract.bet(sp.record(amount=sp.mutez(50000), prediction=True, contract_balance=sp.balance(main_contract.address)).run(sender=player, valid=False))
    # contract_balance = scenario.compute_view(main_contract.get_balance, main_contract.address)
    # contract_balance = scenario.compute_view(main_contract.get_balance, main_contract, main_contract.address)
    # player_balance = scenario.compute_view(main_contract.get_balance, player.address)
    player_balance = scenario.get_view(main_contract.get_balance, player.address)
    # scenario += main_contract.bet(amount=sp.mutez(50000), prediction=True, contract_balance=contract_balance).run(sender=player, valid=False)
    scenario += main_contract.bet(amount=sp.mutez(50000), prediction=True, contract_balance=player_balance).run(sender=player, valid=False)



    # Test finish_game
    scenario += main_contract.finish_game(player=player, refund=sp.mutez(20)).run(sender=oracle)
    scenario.verify(main_contract.data.players[player.address] == sp.mutez(1010))

    # Test finish_game with invalid player
    scenario += main_contract.finish_game(player=sp.test_account("InvalidPlayer"), refund=sp.mutez(20)).run(sender=oracle, valid=False)

    # Test finish_game with non-oracle sender
    scenario += main_contract.finish_game(player=player, refund=sp.mutez(20)).run(sender=owner, valid=False)

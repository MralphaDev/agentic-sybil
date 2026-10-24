from app.agent.context import AnalysisContext
from app.agent.orchestrator import run_agent_investigation

from app.database.queries import get_wallet_events, get_wallet_profile_addresses
from app.features.compute_wallet_feature import compute_wallet_features
from app.features.normalize_wallet_features import normalize_wallet_features
from app.transaction_info_helper.transfer_extractor import extract_wallet_transfers
from app.transaction_graph.first_fund_graph import build_first_fund_graph
from app.transaction_graph.aggregated_tx_graph.builder import build_aggregated_tx_graph
from app.database.connection import open_pool, close_pool

TARGET_TOKEN_MINT = "C2omVhcvt3DDY77S2KZzawFJQeETZofgZ4eNWWkXpump"


def build_test_context() -> AnalysisContext:
    print("Loading wallet events...")
    events = get_wallet_events()
    profile_wallets = set(get_wallet_profile_addresses())

    print("Preparing wallet transfers...")
    wallet_transfers = extract_wallet_transfers(events)

    print("Computing wallet features...")
    wallet_features = normalize_wallet_features(
        compute_wallet_features(events, wallet_transfers)
    )

    print("Building graphs...")
    first_fund_graph = build_first_fund_graph(
        wallet_features,
        profile_wallets,
    )

    aggregated_tx_graph = build_aggregated_tx_graph(
        wallet_transfers,
        profile_wallets,
    )

    return AnalysisContext(
        target_token_mint=TARGET_TOKEN_MINT,
        events=events,
        profile_wallets=profile_wallets,
        wallet_transfers=wallet_transfers,
        wallet_features=wallet_features,
        first_fund_graph=first_fund_graph,
        aggregated_tx_graph=aggregated_tx_graph,
    )


def main() -> None:
    open_pool()

    try:
        context = build_test_context()

        print("\nStarting agent investigation...")
        result = run_agent_investigation(context)

        print("\n=== Investigation Result ===")
        print(f"Complete: {result['investigation_complete']}")
        print(f"Rounds: {result['investigation_round']}")
        print(f"\nInitial observation:\n{result['initial_observation']}")
        print(f"\nFindings:\n{result['findings']}")
        print(f"\nEvidence:\n{result['evidence']}")
        print(f"\nFinal response:\n{result['final_response']}")

    finally:
        close_pool()


if __name__ == "__main__":
    main()

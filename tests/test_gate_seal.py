from ape import reverts
from ape.logging import logger
import pytest

from utils.constants import MAX_SEALABLES, ZERO_ADDRESS


def test_committee_cannot_be_zero_address(
    project, deployer, seal_duration_seconds, sealables, expiry_period
):
    with reverts("sealing committee: zero address"):
        project.GateSeal.deploy(
            ZERO_ADDRESS,
            seal_duration_seconds,
            sealables,
            expiry_period,
            sender=deployer,
        )


def test_seal_duration_cannot_be_zero(
    project, deployer, sealing_committee, sealables, expiry_period
):
    with reverts("seal duration: zero"):
        project.GateSeal.deploy(
            sealing_committee, 0, sealables, expiry_period, sender=deployer
        )


def test_sealables_cannot_be_empty_list(
    project, deployer, sealing_committee, seal_duration_seconds, expiry_period
):
    with reverts("sealables: empty list"):
        project.GateSeal.deploy(
            sealing_committee, seal_duration_seconds, [], expiry_period, sender=deployer
        )


def test_expiry_period_cannot_be_zero(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
):
    with reverts("expiry period: zero"):
        project.GateSeal.deploy(
            sealing_committee, seal_duration_seconds, sealables, 0, sender=deployer
        )


@pytest.mark.parametrize("zero_address_index", range(MAX_SEALABLES))
def test_sealables_cannot_include_zero_address(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    expiry_period,
    zero_address_index,
    generate_sealables,
):
    sealables = generate_sealables(MAX_SEALABLES)
    sealables[zero_address_index] = ZERO_ADDRESS

    with reverts("sealables: includes zero address"):
        project.GateSeal.deploy(
            sealing_committee,
            seal_duration_seconds,
            sealables,
            expiry_period,
            sender=deployer,
        )


def test_sealables_cannot_exceed_max_length(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    expiry_period,
    generate_sealables,
):
    sealables = generate_sealables(MAX_SEALABLES + 1)

    with reverts():
        project.GateSeal.deploy(
            sealing_committee,
            seal_duration_seconds,
            sealables,
            expiry_period,
            sender=deployer,
        )


def test_deploy_params_must_match(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    expiry_period,
):
    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        expiry_period,
        sender=deployer,
    )

    deployed_block_number = gate_seal._cached_receipt.block_number
    deployed_timestamp = project.provider.get_block(deployed_block_number).timestamp
    expiry_timestamp = deployed_timestamp + expiry_period

    assert (
        gate_seal.get_sealing_committee() == sealing_committee
    ), "sealing committee doesn't match"
    assert (
        gate_seal.get_seal_duration_seconds() == seal_duration_seconds
    ), "seal duration doesn't match"
    assert gate_seal.get_sealables() == sealables, "sealables don't match"
    assert (
        gate_seal.get_expiry_timestamp() == expiry_timestamp
    ), "expiry timestamp don't match"
    assert gate_seal.is_expired() == False, "should not be expired"


def test_seal_all(project, gate_seal, sealing_committee, sealables):
    gate_seal.seal(sealables, sender=sealing_committee)
    assert (
        gate_seal.is_expired() == True
    ), "gate seal must be expired immediately after sealing"

    for sealable in sealables:
        assert project.SealableMock.at(sealable).isPaused(), "sealable must be sealed"


def test_seal_partial(project, gate_seal, sealing_committee, sealables):
    sealable_to_seal = sealables[0]

    gate_seal.seal([sealable_to_seal], sender=sealing_committee)
    assert (
        gate_seal.is_expired() == True
    ), "gate seal must be expired immediately after sealing"

    for sealable in sealables:
        sealable_contract = project.SealableMock.at(sealable)
        if sealable == sealable_to_seal:
            assert sealable_contract.isPaused(), "sealable must be sealed"
        else:
            assert not sealable_contract.isPaused(), "sealable must not be sealed"


def test_seal_as_stranger(gate_seal, stranger, sealables):
    with reverts("sender: not SEALING_COMMITTEE"):
        gate_seal.seal(sealables, sender=stranger)


def test_seal_empty_subset(gate_seal, sealing_committee):
    with reverts("sealables: empty subset"):
        gate_seal.seal([], sender=sealing_committee)


def test_seal_nonintersecting_subset(accounts, gate_seal, sealing_committee):
    with reverts("sealables: includes a non-sealable"):
        gate_seal.seal([accounts[0]], sender=sealing_committee)


def test_seal_partially_intersecting_subset(
    accounts, gate_seal, sealing_committee, sealables
):
    with reverts("sealables: includes a non-sealable"):
        gate_seal.seal([sealables[0], accounts[0]], sender=sealing_committee)

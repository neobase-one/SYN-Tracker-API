#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
import logging

import dateutil.parser
import requests

from .data import COINGECKO_BASE_URL, COINGECKO_HISTORIC_URL, POPULATE_CACHE
from .cache import timed_cache, redis_cache

if POPULATE_CACHE:
    from random import randint
    import time

logger = logging.Logger(__name__)


class CoingeckoIDS(Enum):
    HIGH = 'highstreet'
    SYN = 'synapse-2'
    USDT = 'tether'
    USDC = 'usd-coin'
    BUSD = 'binance-usd'
    DAI = 'dai'
    ETH = 'ethereum'
    DOG = 'the-doge-nft'
    NRV = 'nerve-finance'
    MIM = 'magic-internet-money'
    FRAX = 'frax'
    BNB = 'binancecoin'
    AVAX = 'avalanche-2'
    ONE = 'harmony'
    MATIC = 'matic-network'
    FTM = 'fantom'
    MOVR = 'moonriver'
    NFD = 'feisty-doge-nft'
    JUMP = 'hyperjump'
    OHM = 'olympus'
    JGN = 'juggernaut'


CUSTOM = {
    'ethereum': {
        # nUSD
        '0x1b84765de8b7566e4ceaf4d0fd3c5af52d3dde4f': 1,
    },
    'bsc': {
        # nUSD
        '0x23b891e5c62e0955ae2bd185990103928ab817b3': 1,
        # USD-LP
        '0xf0b8b631145d393a767b4387d08aa09969b2dfed': 1,
        # BSC-USD
        '0x55d398326f99059ff775485246999027b3197955': 1,
        '0xdfd717f4e942931c98053d5453f803a1b52838db': 0,
        # JUMP, not really it's price but oh well.
        '0x130025ee738a66e691e6a7a62381cb33c6d9ae83': 0.01,
    },
    'polygon': {
        # nUSD
        '0xb6c473756050de474286bed418b77aeac39b02af': 1,
        '0x81067076dcb7d3168ccf7036117b9d72051205e2': 0,
        # USD-LP
        '0x128a587555d1148766ef4327172129b50ec66e5d': 1,
    },
    'avalanche': {
        # nUSD
        '0xcfc37a6ab183dd4aed08c204d1c2773c0b1bdf46': 1,
        # USD-LP
        '0x55904f416586b5140a0f666cf5acf320adf64846': 1,
    },
    'arbitrum': {
        # nUSD
        '0x2913e812cf0dcca30fb28e6cac3d2dcff4497688': 1,
        # USD-LP
        '0xe264cb5a941f98a391b9d5244378edf79bf5c19e': 1,
    },
    'fantom': {
        # nUSD
        '0xed2a7edd7413021d440b09d654f3b87712abab66': 1,
        # JUMP, not really it's price but oh well.
        '0x78de9326792ce1d6eca0c978753c6953cdeedd73': 0.01,
        # USD-LP
        '0x43cf58380e69594fa2a5682de484ae00edd83e94': 1,
    },
    'harmony': {
        # nUSD
        '0xed2a7edd7413021d440b09d654f3b87712abab66': 1,
    },
    'boba': {
        # nUSD
        '0x6b4712ae9797c199edd44f897ca09bc57628a1cf': 1,
    },
    'moonriver': {},
    'optimism': {},
}

ADDRESS_TO_CGID = {
    'ethereum': {
        '0x71ab77b7dbb4fa7e017bc15090b2163221420282': CoingeckoIDS.HIGH,
        '0x0f2d719407fdbeff09d87557abb7232601fd9f29': CoingeckoIDS.SYN,
        '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2': CoingeckoIDS.ETH,
        '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48': CoingeckoIDS.USDC,
        '0x6b175474e89094c44da98b954eedeac495271d0f': CoingeckoIDS.DAI,
        '0xdac17f958d2ee523a2206206994597c13d831ec7': CoingeckoIDS.USDT,
        '0xbaac2b4491727d78d2b78815144570b9f2fe8899': CoingeckoIDS.DOG,
        '0x853d955acef822db058eb8505911ed77f175b99e': CoingeckoIDS.FRAX,
        '0xca76543cf381ebbb277be79574059e32108e3e65': CoingeckoIDS.OHM,
    },
    'bsc': {
        '0xe9e7cea3dedca5984780bafc599bd69add087d56': CoingeckoIDS.BUSD,
        '0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d': CoingeckoIDS.USDC,
        '0xaa88c603d142c371ea0eac8756123c5805edee03': CoingeckoIDS.DOG,
        '0xa4080f1778e69467e905b8d6f72f6e441f9e9484': CoingeckoIDS.SYN,
        '0x5f4bde007dc06b867f86ebfe4802e34a1ffeed63': CoingeckoIDS.HIGH,
        '0x55d398326f99059ff775485246999027b3197955': CoingeckoIDS.USDT,
        '0x0fe9778c005a5a6115cbe12b0568a2d50b765a51': CoingeckoIDS.NFD,
        '0x42f6f551ae042cbe50c739158b4f0cac0edb9096': CoingeckoIDS.NRV,
        '0xc13b7a43223bb9bf4b69bd68ab20ca1b79d81c75': CoingeckoIDS.JGN,
    },
    'polygon': {
        '0xf8f9efc0db77d8881500bb06ff5d6abc3070e695': CoingeckoIDS.SYN,
        '0x8f3cf7ad23cd3cadbd9735aff958023239c6a063': CoingeckoIDS.DAI,
        '0x2791bca1f2de4661ed88a30c99a7a9449aa84174': CoingeckoIDS.USDC,
        '0xc2132d05d31c914a87c6611c10748aeb04b58e8f': CoingeckoIDS.USDT,
        '0x0a5926027d407222f8fe20f24cb16e103f617046': CoingeckoIDS.NFD,
    },
    'avalanche': {
        '0x1f1e7c893855525b303f99bdf5c3c05be09ca251': CoingeckoIDS.SYN,
        '0xd586e7f844cea2f87f50152665bcbc2c279d8d70': CoingeckoIDS.DAI,
        '0xa7d7079b0fead91f3e65f86e8915cb59c1a4c664': CoingeckoIDS.USDC,
        '0xc7198437980c041c805a1edcba50c1ce5db95118': CoingeckoIDS.USDT,
        '0xf1293574ee43950e7a8c9f1005ff097a9a713959': CoingeckoIDS.NFD,
        '0x19e1ae0ee35c0404f835521146206595d37981ae': CoingeckoIDS.ETH,
    },
    'arbitrum': {
        '0x080f6aed32fc474dd5717105dba5ea57268f46eb': CoingeckoIDS.SYN,
        '0x3ea9b0ab55f34fb188824ee288ceaefc63cf908e': CoingeckoIDS.ETH,
        '0xff970a61a04b1ca14834a43f5de4533ebddb5cc8': CoingeckoIDS.USDC,
        '0xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9': CoingeckoIDS.USDT,
        '0xfea7a6a0b346362bf88a9e4a88416b77a57d6c2a': CoingeckoIDS.MIM,
        '0x82af49447d8a07e3bd95bd0d56f35241523fbab1': CoingeckoIDS.ETH,
    },
    'fantom': {
        '0xe55e19fb4f2d85af758950957714292dac1e25b2': CoingeckoIDS.SYN,
        '0x82f0b8b456c1a451378467398982d4834b6829c1': CoingeckoIDS.MIM,
        '0x04068da6c83afcfa0e13ba15a6696662335d5b75': CoingeckoIDS.USDC,
        '0x049d68029688eabf473097a2fc38ef61633a3c7a': CoingeckoIDS.USDT,
    },
    'harmony': {
        '0xe55e19fb4f2d85af758950957714292dac1e25b2': CoingeckoIDS.SYN,
        '0xef977d2f931c1978db5f6747666fa1eacb0d0339': CoingeckoIDS.DAI,
        '0x985458e523db3d53125813ed68c274899e9dfab4': CoingeckoIDS.USDC,
        '0x3c2b8be99c50593081eaa2a724f0b8285f5aba8f': CoingeckoIDS.USDT,
    },
    'boba': {
        '0xb554a55358ff0382fb21f0a478c3546d1106be8c': CoingeckoIDS.SYN,
        '0xf74195bb8a5cf652411867c5c2c5b8c2a402be35': CoingeckoIDS.DAI,
        '0x5de1677344d3cb0d7d465c10b72a8f60699c062d': CoingeckoIDS.USDT,
        '0x66a2a913e447d6b4bf33efbec43aaef87890fbbc': CoingeckoIDS.USDC,
        '0x96419929d7949d6a801a6909c145c8eef6a40431': CoingeckoIDS.ETH,
        '0xd203de32170130082896b4111edf825a4774c18e': CoingeckoIDS.ETH,
    },
    'moonriver': {
        '0xd80d8688b02b3fd3afb81cdb124f188bb5ad0445': CoingeckoIDS.SYN,
        '0xe96ac70907fff3efee79f502c985a7a21bce407d': CoingeckoIDS.FRAX,
    },
    'optimism': {
        '0x5a5fff6f753d7c11a56a52fe47a177a87e431655': CoingeckoIDS.SYN,
        '0x809dc529f07651bd43a172e8db6f4a7a0d771036': CoingeckoIDS.ETH,
        '0x121ab82b49b2bc4c7901ca46b8277962b4350204': CoingeckoIDS.ETH,
    }
}


@redis_cache()
def get_historic_price(_id: CoingeckoIDS,
                       date: str,
                       currency: str = "usd") -> Decimal:
    # Assume we got `date` as yyyy-mm-dd and we need as dd-mm-yyyy.
    date = datetime.strptime(date, '%Y-%m-%d').strftime('%d-%m-%Y')

    # CG rate limits us @ 10-50 r/m, let's hope this makes us not trigger it.
    if POPULATE_CACHE:
        time.sleep(randint(5, 20))

    r = requests.get(COINGECKO_HISTORIC_URL.format(_id.value, date)).json()

    try:
        return r['market_data']['current_price'][currency]
    except KeyError:
        # CG doesn't have the price.
        return Decimal(0)


def get_historic_price_syn(date: str, currency: str = "usd") -> Decimal:
    dt = dateutil.parser.parse(date)

    # SYN price didn't exist here on CG but was pegged 1:2.5 to NRV.
    if dt < datetime(year=2021, month=8, day=30):
        return get_historic_price(CoingeckoIDS.NRV, date,
                                  currency) / Decimal('2.5')

    return get_historic_price(CoingeckoIDS.SYN, date, currency)


def get_historic_price_for_address(chain: str, address: str,
                                   date: str) -> Decimal:
    if address in CUSTOM[chain]:
        return CUSTOM[chain][address]
    elif ADDRESS_TO_CGID[chain][address] == CoingeckoIDS.SYN:
        return get_historic_price_syn(date)

    return get_historic_price(ADDRESS_TO_CGID[chain][address], date)


def get_price_for_address(chain: str, address: str) -> Decimal:
    if address in CUSTOM[chain]:
        return CUSTOM[chain][address]

    if address not in ADDRESS_TO_CGID[chain]:
        logger.warning(f'returning amount 0 for token {address} on {chain}')
        return Decimal(0)

    return get_price_coingecko(ADDRESS_TO_CGID[chain][address])


@timed_cache(60 * 10, maxsize=500)
def get_price_coingecko(_id: CoingeckoIDS, currency: str = "usd") -> Decimal:
    # CG rate limits us @ 10-50 r/m, let's hope this makes us not trigger it.
    if POPULATE_CACHE:
        time.sleep(randint(5, 20))

    r = requests.get(COINGECKO_BASE_URL.format(_id.value, currency))
    return Decimal(r.json()[_id.value][currency])


def init() -> None:
    """Fire up the LRU cache."""
    [get_price_coingecko(x) for x in CoingeckoIDS]
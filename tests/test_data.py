def main(): ...


# test system data
sol_data = {
    "id64": 10477373803,
    "name": "Sol",
    "mainstar": "G",
    "coords": {"x": 0.0, "y": 0.0, "z": 0.0},
}
wise_data = {
    "id64": 22959284702024,
    "name": "WISE 0410+1502",
    "mainstar": "Y (Brown dwarf) Star",
    "coords": {"x": -0.46875, "y": -6.125, "z": -12.59375},
}

alpha_centauri_data = {
    "id64": 1178708478315,
    "name": "Alpha Centauri",
    "mainstar": "G",
    "coords": {"x": 3.03125, "y": -0.09375, "z": 3.15625},
}

luhman_16_data = {
    "id64": 22960358574928,
    "name": "Luhman 16",
    "mainstar": "L",
    "coords": {"x": 6.3125, "y": 0.59375, "z": 1.71875},
    "distance": 3.647692978102735,
}

# test neighbors data
truncated_sol_neighbors = [
    {
        "id64": 10477373803,
        "name": "Sol",
        "mainstar": "G",
        "coords": {"x": 0.0, "y": 0.0, "z": 0.0},
        "distance": 0.0,
    },
    {
        "id64": 1178708478315,
        "name": "Alpha Centauri",
        "mainstar": "G",
        "coords": {"x": 3.03125, "y": -0.09375, "z": 3.15625},
        "distance": 4.377120022057882,
    },
]

truncated_alpha_centauri_neighbors = [
    {
        "id64": 1178708478315,
        "name": "Alpha Centauri",
        "mainstar": "G",
        "coords": {"x": 3.03125, "y": -0.09375, "z": 3.15625},
        "distance": 0,
    },
    {
        "id64": 22960358574928,
        "name": "Luhman 16",
        "mainstar": "L",
        "coords": {"x": 6.3125, "y": 0.59375, "z": 1.71875},
        "distance": 3.647692978102735,
    },
]

truncated_luhman_16_neighbors = [
    {
        "id64": 22960358574928,
        "name": "Luhman 16",
        "mainstar": "L",
        "coords": {"x": 6.3125, "y": 0.59375, "z": 1.71875},
        "distance": 0,
    },
    {
        "id64": 1178708478315,
        "name": "Alpha Centauri",
        "mainstar": "G",
        "coords": {"x": 3.03125, "y": -0.09375, "z": 3.15625},
        "distance": 3.647692978102735,
    },
    {
        "id64": 10477373803,
        "name": "Sol",
        "mainstar": "G",
        "coords": {"x": 0, "y": 0, "z": 0},
        "distance": 6.569193015508069,
    },
]


sol_additional_neighbors = [
    {
        "id64": 18263140541865,
        "name": "Barnard's Star",
        "mainstar": "M",
        "coords": {"x": -3.03125, "y": 1.375, "z": 4.9375},
        "distance": 5.954662695107087,
    },
    {
        "id64": 22960358574928,
        "name": "Luhman 16",
        "mainstar": "L",
        "coords": {"x": 6.3125, "y": 0.59375, "z": 1.71875},
        "distance": 6.569193015508069,
    },
]

sol_complete_info = {
    "id64": 10477373803,
    "name": "Sol",
    "mainstar": "G",
    "coords": {"x": 0, "y": 0, "z": 0},
    "neighbors": [
        {
            "id64": 10477373803,
            "name": "Sol",
            "mainstar": "G",
            "coords": {"x": 0, "y": 0, "z": 0},
            "distance": 0,
        },
        {
            "id64": 1178708478315,
            "name": "Alpha Centauri",
            "mainstar": "G",
            "coords": {"x": 3.03125, "y": -0.09375, "z": 3.15625},
            "distance": 4.377120022057882,
        },
        {
            "id64": 18263140541865,
            "name": "Barnard's Star",
            "mainstar": "M",
            "coords": {"x": -3.03125, "y": 1.375, "z": 4.9375},
            "distance": 5.954662695107087,
        },
        {
            "id64": 22960358574928,
            "name": "Luhman 16",
            "mainstar": "L",
            "coords": {"x": 6.3125, "y": 0.59375, "z": 1.71875},
            "distance": 6.569193015508069,
        },
        {
            "id64": 58144730663760,
            "name": "WISE 0855-0714",
            "mainstar": "Y",
            "coords": {"x": 6.53125, "y": -2.15625, "z": 2.03125},
            "distance": 7.17165372752338,
        },
        {
            "id64": 24860210308521,
            "name": "Wolf 359",
            "mainstar": "M",
            "coords": {"x": 3.875, "y": 6.46875, "z": -1.90625},
            "distance": 7.7777979290413555,
        },
        {
            "id64": 9467047519657,
            "name": "Lalande 21185",
            "mainstar": "M",
            "coords": {"x": 0.3125, "y": 7.5625, "z": -3.375},
            "distance": 8.287320887958906,
        },
        {
            "id64": 18263140476329,
            "name": "UV Ceti",
            "mainstar": "M",
            "coords": {"x": -0.1875, "y": -8.3125, "z": -2.125},
            "distance": 8.581866784097736,
        },
        {
            "id64": 121569805492,
            "name": "Sirius",
            "mainstar": "A",
            "coords": {"x": 6.25, "y": -1.28125, "z": -5.75},
            "distance": 8.588748544607649,
        },
        {
            "id64": 7268024264105,
            "name": "Ross 154",
            "mainstar": "M",
            "coords": {"x": -1.9375, "y": -1.84375, "z": 9.3125},
            "distance": 9.688961583291576,
        },
        {
            "id64": 4374164146539,
            "name": "Yin Sector CL-Y d127",
            "mainstar": "K",
            "coords": {"x": 1.0625, "y": 3.875, "z": -9},
            "distance": 9.85619253312353,
        },
        {
            "id64": 4339804408171,
            "name": "Duamta",
            "mainstar": "F",
            "coords": {"x": 2.1875, "y": 6.625, "z": -7},
            "distance": 9.88310585038934,
        },
    ],
}

sol_complete_neighbors = [
    {
        "id64": 10477373803,
        "name": "Sol",
        "mainstar": "G",
        "coords": {"x": 0, "y": 0, "z": 0},
        "distance": 0,
    },
    {
        "id64": 1178708478315,
        "name": "Alpha Centauri",
        "mainstar": "G",
        "coords": {"x": 3.03125, "y": -0.09375, "z": 3.15625},
        "distance": 4.377120022057882,
    },
    {
        "id64": 18263140541865,
        "name": "Barnard's Star",
        "mainstar": "M",
        "coords": {"x": -3.03125, "y": 1.375, "z": 4.9375},
        "distance": 5.954662695107087,
    },
    {
        "id64": 22960358574928,
        "name": "Luhman 16",
        "mainstar": "L",
        "coords": {"x": 6.3125, "y": 0.59375, "z": 1.71875},
        "distance": 6.569193015508069,
    },
    {
        "id64": 58144730663760,
        "name": "WISE 0855-0714",
        "mainstar": "Y",
        "coords": {"x": 6.53125, "y": -2.15625, "z": 2.03125},
        "distance": 7.17165372752338,
    },
    {
        "id64": 24860210308521,
        "name": "Wolf 359",
        "mainstar": "M",
        "coords": {"x": 3.875, "y": 6.46875, "z": -1.90625},
        "distance": 7.7777979290413555,
    },
    {
        "id64": 9467047519657,
        "name": "Lalande 21185",
        "mainstar": "M",
        "coords": {"x": 0.3125, "y": 7.5625, "z": -3.375},
        "distance": 8.287320887958906,
    },
    {
        "id64": 18263140476329,
        "name": "UV Ceti",
        "mainstar": "M",
        "coords": {"x": -0.1875, "y": -8.3125, "z": -2.125},
        "distance": 8.581866784097736,
    },
    {
        "id64": 121569805492,
        "name": "Sirius",
        "mainstar": "A",
        "coords": {"x": 6.25, "y": -1.28125, "z": -5.75},
        "distance": 8.588748544607649,
    },
    {
        "id64": 7268024264105,
        "name": "Ross 154",
        "mainstar": "M",
        "coords": {"x": -1.9375, "y": -1.84375, "z": 9.3125},
        "distance": 9.688961583291576,
    },
    {
        "id64": 4374164146539,
        "name": "Yin Sector CL-Y d127",
        "mainstar": "K",
        "coords": {"x": 1.0625, "y": 3.875, "z": -9},
        "distance": 9.85619253312353,
    },
    {
        "id64": 4339804408171,
        "name": "Duamta",
        "mainstar": "F",
        "coords": {"x": 2.1875, "y": 6.625, "z": -7},
        "distance": 9.88310585038934,
    },
]

barnards_star_complete_info = {
    "id64": 18263140541865,
    "name": "Barnard's Star",
    "mainstar": "M",
    "coords": {"x": -3.03125, "y": 1.375, "z": 4.9375},
    "neighbors": [
        {
            "id64": 18263140541865,
            "name": "Barnard's Star",
            "mainstar": "M",
            "coords": {"x": -3.03125, "y": 1.375, "z": 4.9375},
            "distance": 0,
        },
        {
            "id64": 7268024264105,
            "name": "Ross 154",
            "mainstar": "M",
            "coords": {"x": -1.9375, "y": -1.84375, "z": 9.3125},
            "distance": 5.540511314400504,
        },
        {
            "id64": 10477373803,
            "name": "Sol",
            "mainstar": "G",
            "coords": {"x": 0, "y": 0, "z": 0},
            "distance": 5.954662695107087,
        },
        {
            "id64": 1178708478315,
            "name": "Alpha Centauri",
            "mainstar": "G",
            "coords": {"x": 3.03125, "y": -0.09375, "z": 3.15625},
            "distance": 6.487216997680901,
        },
        {
            "id64": 16064117286313,
            "name": "Wolf 1061",
            "mainstar": "M",
            "coords": {"x": -0.84375, "y": 5.46875, "z": 12.84375},
            "distance": 9.168027834545443,
        },
        {
            "id64": 5856288576210,
            "name": "61 Cygni",
            "mainstar": "K",
            "coords": {"x": -11.21875, "y": -1.1875, "z": 1.40625},
            "distance": 9.277461347938885,
        },
        {
            "id64": 13864825595305,
            "name": "Struve 2398",
            "mainstar": "M",
            "coords": {"x": -10.625, "y": 4.75, "z": 0.09375},
            "distance": 9.61860583062847,
        },
        {
            "id64": 22960358574928,
            "name": "Luhman 16",
            "mainstar": "L",
            "coords": {"x": 6.3125, "y": 0.59375, "z": 1.71875},
            "distance": 9.913443760242956,
        },
    ],
}

s_61_cygni_complet_info = {
    "id64": 5856288576210,
    "name": "61 Cygni",
    "mainstar": "K",
    "coords": {"x": -11.21875, "y": -1.1875, "z": 1.40625},
    "neighbors": [
        {
            "id64": 5856288576210,
            "name": "61 Cygni",
            "mainstar": "K",
            "coords": {"x": -11.21875, "y": -1.1875, "z": 1.40625},
            "distance": 0,
        },
        {
            "id64": 22660918617513,
            "name": "Kruger 60",
            "mainstar": "M",
            "coords": {"x": -12.625, "y": 0, "z": -3.40625},
            "distance": 5.152460728865384,
        },
        {
            "id64": 22958211091280,
            "name": "V1581 Cygni",
            "mainstar": "M",
            "coords": {"x": -14.9375, "y": 2.25, "z": 2.9375},
            "distance": 5.290579776829757,
        },
        {
            "id64": 5366025046864,
            "name": "Ross 248",
            "mainstar": "M",
            "coords": {"x": -9.3125, "y": -3.03125, "z": -3.40625},
            "distance": 5.494848439675111,
        },
        {
            "id64": 13864825595305,
            "name": "Struve 2398",
            "mainstar": "M",
            "coords": {"x": -10.625, "y": 4.75, "z": 0.09375},
            "distance": 6.10975462375536,
        },
        {
            "id64": 7267755828641,
            "name": "Groombridge 34",
            "mainstar": "M",
            "coords": {"x": -9.90625, "y": -3.6875, "z": -5.09375},
            "distance": 7.086794497514373,
        },
        {
            "id64": 24859941873065,
            "name": "EV Lacertae",
            "mainstar": "M",
            "coords": {"x": -16, "y": -3.78125, "z": -3.15625},
            "distance": 7.099598360118691,
        },
        {
            "id64": 18263140541865,
            "name": "Barnard's Star",
            "mainstar": "M",
            "coords": {"x": -3.03125, "y": 1.375, "z": 4.9375},
            "distance": 9.277461347938885,
        },
        {
            "id64": 11665802339753,
            "name": "LHS 450",
            "mainstar": "M",
            "coords": {"x": -12.40625, "y": 7.8125, "z": -1.875},
            "distance": 9.652810876242215,
        },
        {
            "id64": 306253399220,
            "name": "Altair",
            "mainstar": "A",
            "coords": {"x": -12.3125, "y": -2.75, "z": 11},
            "distance": 9.78149959745437,
        },
        {
            "id64": 5366025177936,
            "name": "WISE 1506+7027",
            "mainstar": "T",
            "coords": {"x": -7.375, "y": 7.09375, "z": -2.4375},
            "distance": 9.905954254260415,
        },
    ],
}

ross_248_complete_info = {
    "id64": 5366025046864,
    "name": "Ross 248",
    "mainstar": "M",
    "coords": {"x": -9.3125, "y": -3.03125, "z": -3.40625},
    "neighbors": [
        {
            "id64": 5366025046864,
            "name": "Ross 248",
            "mainstar": "M",
            "coords": {"x": -9.3125, "y": -3.03125, "z": -3.40625},
            "distance": 0,
        },
        {
            "id64": 7267755828641,
            "name": "Groombridge 34",
            "mainstar": "M",
            "coords": {"x": -9.90625, "y": -3.6875, "z": -5.09375},
            "distance": 1.9054814024282682,
        },
        {
            "id64": 22660918617513,
            "name": "Kruger 60",
            "mainstar": "M",
            "coords": {"x": -12.625, "y": 0, "z": -3.40625},
            "distance": 4.490115011054839,
        },
        {
            "id64": 5856288576210,
            "name": "61 Cygni",
            "mainstar": "K",
            "coords": {"x": -11.21875, "y": -1.1875, "z": 1.40625},
            "distance": 5.494848439675111,
        },
        {
            "id64": 24859941873065,
            "name": "EV Lacertae",
            "mainstar": "M",
            "coords": {"x": -16, "y": -3.78125, "z": -3.15625},
            "distance": 6.734066843297592,
        },
        {
            "id64": 13864825595305,
            "name": "Struve 2398",
            "mainstar": "M",
            "coords": {"x": -10.625, "y": 4.75, "z": 0.09375},
            "distance": 8.632526154753311,
        },
        {
            "id64": 670685996457,
            "name": "van Maanen's Star",
            "mainstar": "White Dwarf (D) Star",
            "coords": {"x": -6.3125, "y": -11.6875, "z": -4.125},
            "distance": 9.18951933590653,
        },
        {
            "id64": 5367098657608,
            "name": "Teegarden's star",
            "mainstar": "M",
            "coords": {"x": -3.375, "y": -7.46875, "z": -9.34375},
            "distance": 9.497326926562021,
        },
        {
            "id64": 13864825529761,
            "name": "TZ Arietis",
            "mainstar": "M",
            "coords": {"x": -5.375, "y": -10.59375, "z": -8.5},
            "distance": 9.931847842295008,
        },
        {
            "id64": 22958211091280,
            "name": "V1581 Cygni",
            "mainstar": "M",
            "coords": {"x": -14.9375, "y": 2.25, "z": 2.9375},
            "distance": 9.988763217986499,
        },
    ],
}

if __name__ == "__main__":
    main()

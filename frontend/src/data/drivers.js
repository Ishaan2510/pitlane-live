// Single source of truth for 2026 driver roster.
// Used by TheGrid.vue (display) and PredictRace.vue (prediction picker).

export const TEAM_COLORS = {
  'Alpine':          '#FF87BC',
  'Aston Martin':    '#229971',
  'Audi':            '#ffffff',
  'Cadillac':        '#CC0000',
  'Ferrari':         '#E8002D',
  'Haas':            '#B6BABD',
  'McLaren':         '#FF8000',
  'Mercedes':        '#27F4D2',
  'Racing Bulls':    '#6692FF',
  'Red Bull Racing': '#3671C6',
  'Williams':        '#64C4FF',
}

export const DRIVERS_2026 = [
  { code:'GAS', number:10, firstName:'Pierre',    lastName:'Gasly',      team:'Alpine'          },
  { code:'COL', number:43, firstName:'Franco',    lastName:'Colapinto',  team:'Alpine'          },
  { code:'ALO', number:14, firstName:'Fernando',  lastName:'Alonso',     team:'Aston Martin'    },
  { code:'STR', number:18, firstName:'Lance',     lastName:'Stroll',     team:'Aston Martin'    },
  { code:'HUL', number:27, firstName:'Nico',      lastName:'Hulkenberg', team:'Audi'            },
  { code:'BOR', number:5,  firstName:'Gabriel',   lastName:'Bortoleto',  team:'Audi'            },
  { code:'PER', number:11, firstName:'Sergio',    lastName:'Perez',      team:'Cadillac'        },
  { code:'BOT', number:77, firstName:'Valtteri',  lastName:'Bottas',     team:'Cadillac'        },
  { code:'LEC', number:16, firstName:'Charles',   lastName:'Leclerc',    team:'Ferrari'         },
  { code:'HAM', number:44, firstName:'Lewis',     lastName:'Hamilton',   team:'Ferrari'         },
  { code:'OCO', number:31, firstName:'Esteban',   lastName:'Ocon',       team:'Haas'            },
  { code:'BEA', number:87, firstName:'Oliver',    lastName:'Bearman',    team:'Haas'            },
  { code:'NOR', number:4,  firstName:'Lando',     lastName:'Norris',     team:'McLaren'         },
  { code:'PIA', number:81, firstName:'Oscar',     lastName:'Piastri',    team:'McLaren'         },
  { code:'RUS', number:63, firstName:'George',    lastName:'Russell',    team:'Mercedes'        },
  { code:'ANT', number:12, firstName:'Kimi',      lastName:'Antonelli',  team:'Mercedes'        },
  { code:'LAW', number:30, firstName:'Liam',      lastName:'Lawson',     team:'Racing Bulls'    },
  { code:'LIN', number:41, firstName:'Arvid',     lastName:'Lindblad',   team:'Racing Bulls'    },
  { code:'VER', number:1,  firstName:'Max',       lastName:'Verstappen', team:'Red Bull Racing' },
  { code:'HAD', number:6,  firstName:'Isack',     lastName:'Hadjar',     team:'Red Bull Racing' },
  { code:'SAI', number:55, firstName:'Carlos',    lastName:'Sainz',      team:'Williams'        },
  { code:'ALB', number:23, firstName:'Alexander', lastName:'Albon',      team:'Williams'        },
]

export function teamColor(team) {
  return TEAM_COLORS[team] || '#888'
}

export function driverByCode(code) {
  return DRIVERS_2026.find(d => d.code === code.toUpperCase())
}
const express = require('express');
const crypto = require('crypto');
const cookieSession = require('cookie-session');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 8080;
const FLAG = process.env.FLAG || 'dice{test_flag}';

app.use(express.json());
app.use(cookieSession({
  name: 'session',
  keys: [crypto.randomBytes(32).toString('hex')],
  maxAge: 24 * 60 * 60 * 1000
}));

const PICKAXES = [
  { name: 'Wooden Pickaxe',  range: 5,   cost: 0,     tier: 0 },
  { name: 'Stone Pickaxe',   range: 15,  cost: 100,   tier: 1 },
  { name: 'Iron Pickaxe',    range: 40,  cost: 500,   tier: 2 },
  { name: 'Gold Pickaxe',    range: 100, cost: 5000,  tier: 3 },
];

const FLAG_COST = 1_000_000;
const STARTING_BALANCE = 0;
const STARTING_ENERGY = 250;
const WORLD_SEED = 42;

// big rock become small paycheck
const HAULING_RATE = 0.95;

const ORES = {
  surface:  { name: 'Surface',  reward: 10,   tier: 0 },
  stone:    { name: 'Stone',    reward: 10,   tier: 0 },
  coal:     { name: 'Coal',     reward: 80,   tier: 0 },
  iron:     { name: 'Iron',     reward: 300,  tier: 1 },
  gold:     { name: 'Gold',     reward: 750,  tier: 2 },
  diamond:  { name: 'Diamond',  reward: 1500, tier: 3 },
};

function getBlockType(x, y) {
  if (y >= 1) return 'sky';
  if (y === 0) return 'surface';

  const hash = crypto.createHash('md5').update(`${WORLD_SEED}:${x}:${y}`).digest();
  const roll = hash.readUInt32BE(0) / 0xFFFFFFFF;

  if (y <= -50 && roll < 0.04) return 'diamond';
  if (y <= -30 && roll < 0.10) return 'gold';
  if (y <= -15 && roll < 0.20) return 'iron';
  if (y <= -1  && roll < 0.35) return 'coal';
  return 'stone';
}

const users = new Map();

function createUser(username, password) {
  users.set(username, {
    password,
    balance: STARTING_BALANCE,
    energy: STARTING_ENERGY,
    pickaxe: 0,
    x: 0,
    y: 0,
    mined: {},
    log: [],
    started: false,
  });
}

function requireAuth(req, res, next) {
  if (!req.session.username || !users.has(req.session.username)) {
    return res.status(401).json({ error: 'not logged in' });
  }
  req.user = users.get(req.session.username);
  req.username = req.session.username;
  next();
}

function requireStarted(req, res, next) {
  if (!req.user.started) {
    return res.status(400).json({ error: 'game not started — call /api/start first' });
  }
  next();
}

app.post('/api/register', (req, res) => {
  const { username, password } = req.body;
  if (!username || !password) {
    return res.status(400).json({ error: 'username and password required' });
  }
  if (typeof username !== 'string' || typeof password !== 'string') {
    return res.status(400).json({ error: 'invalid input' });
  }
  if (username.length < 5 || username.length > 32) {
    return res.status(400).json({ error: 'username must be 5-32 characters' });
  }
  if (password.length < 7 || password.length > 64) {
    return res.status(400).json({ error: 'password must be 7-64 characters' });
  }
  if (password.includes(username)) {
    return res.status(400).json({ error: 'password cannot contain username' });
  }
  if (users.has(username)) {
    return res.status(400).json({ error: 'username taken' });
  }
  createUser(username, password);
  req.session.username = username;
  res.json({ success: true });
});

app.post('/api/login', (req, res) => {
  const { username, password } = req.body;
  if (!username || !password) {
    return res.status(400).json({ error: 'username and password required' });
  }
  const user = users.get(username);
  if (!user || user.password !== password) {
    return res.status(401).json({ error: 'invalid credentials' });
  }
  req.session.username = username;
  res.json({ success: true });
});

app.post('/api/logout', (req, res) => {
  req.session = null;
  res.json({ success: true });
});

app.get('/api/state', requireAuth, (req, res) => {
  const user = req.user;
  const pickaxe = PICKAXES[user.pickaxe];

  const GR = 24;
  const grid = {};
  for (let dy = -GR; dy <= GR; dy++) {
    for (let dx = -GR; dx <= GR; dx++) {
      const bx = user.x + dx, by = user.y + dy;
      const key = bx + ',' + by;
      grid[key] = {
        type: getBlockType(bx, by),
        mined: !!user.mined[key],
      };
    }
  }

  res.json({
    username: req.username,
    started: user.started,
    balance: user.balance,
    energy: user.energy,
    pickaxe: user.pickaxe,
    pickaxeInfo: pickaxe,
    x: user.x,
    y: user.y,
    blocksMined: Object.keys(user.mined).length,
    log: user.log.slice(-20),
    pickaxes: PICKAXES,
    flagCost: FLAG_COST,
    haulingRate: HAULING_RATE,
    grid,
  });
});

app.post('/api/start', requireAuth, (req, res) => {
  const user = req.user;
  const x = Math.floor(+req.body.x);

  if (isNaN(x) || !isFinite(x)) {
    return res.status(400).json({ error: 'invalid x coordinate' });
  }

  user.balance = STARTING_BALANCE;
  user.energy = STARTING_ENERGY;
  user.pickaxe = 0;
  user.x = x;
  user.y = 1;
  user.mined = {};
  user.log = [];
  user.started = true;

  res.json({ success: true, x: user.x, y: user.y });
});

app.post('/api/move', requireAuth, requireStarted, (req, res) => {
  const user = req.user;
  const moves = Array.isArray(req.body.moves) ? req.body.moves
    : [{ x: req.body.x, y: req.body.y }];

  if (moves.length < 1 || moves.length > 32) {
    return res.status(400).json({ error: 'between 1 and 32 moves allowed' });
  }

  let cx = user.x, cy = user.y;
  for (let i = 0; i < moves.length; i++) {
    const x = Math.floor(+moves[i].x);
    const y = Math.floor(+moves[i].y);

    if (isNaN(x) || isNaN(y)) {
      return res.status(400).json({ error: 'invalid coordinates', step: i });
    }

    const adx = Math.abs(x - cx);
    const ady = Math.abs(y - cy);
    if (adx + ady !== 1) {
      return res.status(400).json({ error: 'can only move one step at a time', step: i });
    }

    if (y > 1) {
      return res.status(400).json({ error: '', step: i });
    }

    const key = x + ',' + y;
    if (y < 1 && !user.mined[key]) {
      return res.status(400).json({ error: '', step: i });
    }

    cx = x;
    cy = y;
  }

  user.x = cx;
  user.y = cy;

  res.json({ success: true, x: user.x, y: user.y });
});

app.post('/api/dig', requireAuth, requireStarted, (req, res) => {
  const user = req.user;
  const { direction } = req.body;

  if (!['up', 'down', 'left', 'right'].includes(direction)) {
    return res.status(400).json({ error: 'invalid direction' });
  }

  const pickaxe = PICKAXES[user.pickaxe];

  if (user.energy < 1) {
    return res.status(400).json({ error: 'no energy left' });
  }

  let dx = 0, dy = 0;
  if (direction === 'left') dx = -1;
  if (direction === 'right') dx = 1;
  if (direction === 'down') dy = -1;
  if (direction === 'up') dy = 1;

  let mined = {};
  let earnings = 0;
  let cx = user.x;
  let cy = user.y;
  let remaining = pickaxe.range;

  while (remaining > 0) {
    cx += dx;
    cy += dy;

    if (cy > 0) break;

    const key = cx + ',' + cy;

    if (user.mined[key]) {
      remaining--;
      continue;
    }

    const blockType = getBlockType(cx, cy);
    const ore = ORES[blockType];
    if (!ore) break;

    if (ore.tier > pickaxe.tier) break;

    mined[key] = true;
    earnings += ore.reward;

    remaining--;
  }

  const blocks = Object.keys(mined);

  if (blocks.length === 0) {
    return res.status(400).json({ error: 'nothing to mine' });
  }

  let haulBase = 0;
  for (const key of blocks) {
    const [bx, by] = key.split(',').map(Number);
    const ore = ORES[getBlockType(bx, by)];
    haulBase += ore.reward;
  }
  const cost = Math.floor(haulBase * HAULING_RATE);
  const net = earnings - cost;

  user.energy -= 1;

  for (const key of blocks) {
    user.mined[key] = true;
  }

  user.balance += net;

  const entry = {
    time: Date.now(),
    direction,
    blocks: blocks.length,
    earnings,
    cost,
    net,
    position: { x: user.x, y: user.y },
  };
  user.log.push(entry);
  if (user.log.length > 50) user.log.shift();

  res.json({
    success: true,
    blocks: blocks.length,
    earnings,
    cost,
    net,
    balance: user.balance,
    energy: user.energy,
    position: { x: user.x, y: user.y },
  });
});

app.post('/api/buy', requireAuth, requireStarted, (req, res) => {
  const user = req.user;
  const { item } = req.body;

  if (item === 'flag') {
    if (user.balance < FLAG_COST) {
      return res.status(400).json({ error: 'not enough DiceCoin' });
    }
    user.balance -= FLAG_COST;
    return res.json({ success: true, flag: FLAG });
  }

  const tierIndex = Math.floor(+item);
  if (isNaN(tierIndex) || tierIndex < 0 || tierIndex >= PICKAXES.length) {
    return res.status(400).json({ error: 'invalid item' });
  }

  const pickaxe = PICKAXES[tierIndex];
  if (user.pickaxe >= tierIndex) {
    return res.status(400).json({ error: 'you already have this or better' });
  }
  if (user.balance < pickaxe.cost) {
    return res.status(400).json({ error: 'not enough DiceCoin' });
  }

  user.balance -= pickaxe.cost;
  user.pickaxe = tierIndex;

  res.json({ success: true, pickaxe: pickaxe.name });
});

app.use(express.static(path.join(__dirname, 'public')));
app.get('/', (_req, res) => res.sendFile(path.join(__dirname, 'public', 'index.html')));

app.listen(PORT, (err) => err ? console.error(err) : console.log(`web/diceminer running on port ${PORT}`));

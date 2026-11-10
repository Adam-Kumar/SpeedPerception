-- Speed Perception User Study 10Hz UDP Telemetry Protocol (127.0.0.1:64256)
local M = {}

local simTime = 0

local function init()
  simTime = 0
end

local function reset()
  simTime = 0
end

local function getAddress()
  return "127.0.0.1"
end

local function getPort()
  return 64256
end

local function getMaxUpdateRate()
  return 10
end

local function isPhysicsStepUsed()
  return false
end

local function getStructDefinition()
  return [[
    float time;
    float posX;
    float posY;
    float posZ;
    float velX;
    float velY;
    float velZ;
    float speedKmh;
    float throttle;
    float brake;
    float steering;
  ]]
end

local function fillStruct(o, dtSim)
  simTime = simTime + dtSim
  local px, py, pz = obj:getPositionXYZ()
  local vx, vy, vz = obj:getVelocityXYZ()
  local speedMs = math.sqrt(vx * vx + vy * vy + vz * vz)

  o.time = simTime
  o.posX = px
  o.posY = py
  o.posZ = pz
  o.velX = vx
  o.velY = vy
  o.velZ = vz
  o.speedKmh = speedMs * 3.6
  o.throttle = electrics.values.throttle or 0
  o.brake = electrics.values.brake or 0
  o.steering = electrics.values.steering or 0
end

M.init = init
M.reset = reset
M.getAddress = getAddress
M.getPort = getPort
M.getMaxUpdateRate = getMaxUpdateRate
M.isPhysicsStepUsed = isPhysicsStepUsed
M.getStructDefinition = getStructDefinition
M.fillStruct = fillStruct

return M

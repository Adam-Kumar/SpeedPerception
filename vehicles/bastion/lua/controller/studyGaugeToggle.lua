-- This Source Code Form is subject to the terms of the bCDDL, v. 1.1.
-- Speed Perception User Study: Live Speedometer + RPM Needle & Digital Speed Toggle
-- Press 'G' in-game to toggle gauges ON (Preparation / Familiarization) or OFF (User Study).

local M = {}
M.type = "auxiliary"

-- Default to hidden (true) for the user study; press 'G' to toggle ON during preparation phase
local gaugesHidden = true

local targetMeshes = {
  bastion_speedometer_needle = true,
  bastion_tachometer_needle = true
}

local function applyGaugeState()
  electrics.values.study_hide_gauges = gaugesHidden and 1 or 0
  if v and v.data and v.data.props then
    for _, prop in pairs(v.data.props) do
      if type(prop) == "table" and prop.mesh and targetMeshes[prop.mesh] then
        prop.hidden = gaugesHidden
      end
    end
  end
end

local function toggleGauges()
  gaugesHidden = not gaugesHidden
  applyGaugeState()
  if guihooks and guihooks.message then
    if gaugesHidden then
      guihooks.message("User Study Mode: Speedometer & RPM Gauges HIDDEN (Press G to show)", 4, "studyGaugeToggle")
    else
      guihooks.message("Preparation Mode: Speedometer & RPM Gauges VISIBLE (Press G to hide)", 4, "studyGaugeToggle")
    end
  end
end

local function setGaugesHidden(hidden)
  gaugesHidden = not not hidden
  applyGaugeState()
end

local function updateGFX(dt)
  applyGaugeState()
end

local function init(jbeamData)
  if jbeamData and jbeamData.startHidden ~= nil then
    gaugesHidden = jbeamData.startHidden
  end
  applyGaugeState()
end

local function reset()
  applyGaugeState()
end

M.init = init
M.reset = reset
M.updateGFX = updateGFX
M.toggleGauges = toggleGauges
M.setGaugesHidden = setGaugesHidden

return M

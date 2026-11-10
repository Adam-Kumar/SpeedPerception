// console.log("load gaugesScreen");
angular.module('gaugesScreen', [])

  .controller('GaugesScreenController', function ($scope, $element, $window) {
    "use strict";
    var vm = this;

    var svg;

    var speedoDisplay = { };
    var infoDisplay = {};
    var electrics = {lights:{} };
    var gagues = {fuel:{},temp:{}};
    let gmeter = {};
    let dragLayer = {}

    var speedoInitialised = true;
    var cachedVal = { temp:-100, fuel:-100, gForcesVisible: false, dragMode: false};

    var ready = false;
    var lastIgnitionLevel = -1;
    var startupScreen = null;

    var unitTorque = "imperial";
    var unitPower = "hp";
    var unitLength = "metric"
    var unitspeedConv = 3.6;

    function updateClock(){
      let date = new Date();
      let h = date.getHours(); // 0 - 23
      let m = date.getMinutes(); // 0 - 59
      let s = date.getSeconds();
      //h = h%12 +1
      m = (m < 10)? "0"+m : m
      let timeStr = h +":"+m //+":" + s
      speedoDisplay.clockTxt.text(timeStr)
      setTimeout(updateClock, 1000);
    }

    // Make sure SVG is loaded
    $scope.onSVGLoaded = function () {
      svg = $element[0].children[0].children[0];
      startupScreen = document.getElementById("startupScreen");

      // speedometer
      speedoDisplay.root = hu('#layer6', svg); //label= txt
      speedoDisplay.rootspeedo = hu('#speedometer', svg); //label= txt
      speedoDisplay.speedometerText = hu('#speedometerText', speedoDisplay.rootspeedo)
      speedoDisplay.speedUnit = hu('#speedUnit', speedoDisplay.rootspeedo);
      speedoDisplay.clockTxt = hu('#clock_txt', speedoDisplay.root)
      // speedoDisplay.speedValue = hu('#speedValue', speedoDisplay.speedometerText);
      // speedoDisplay.speedValues = []
      // speedoDisplay.speedValues.push(speedoDisplay.speedValue.n.querySelector("#tspanSpdUnit") );
      // speedoDisplay.speedValues.push(speedoDisplay.speedValue.n.querySelector("#tspanSpdDizaine") );
      // speedoDisplay.speedValues.push(speedoDisplay.speedValue.n.querySelector("#tspanSpdCentaine") );
      speedoDisplay.gear = hu('#gear_txt', speedoDisplay.root);

      gagues.fuel.needle = hu('#needle_fuel', svg);
      gagues.fuel.grad = hu('#linGrad_fuel', svg);
      gagues.fuel.path = hu('#path_fuel', svg);

      gagues.temp.needle = hu('#needle_temp', svg);
      gagues.temp.grad = hu('#linGrad_temp', svg);
      gagues.temp.path = hu('#path_temp', svg);


      electrics.temp_logo = hu("#temp_logo", electrics.root);
      electrics.fuel_logo = hu("#fuel_logo", electrics.root);
      electrics.odo_txt = hu("#odo_txt", electrics.root);
      electrics.mode_txt = hu("#mode_txt", electrics.root);
      electrics.mode_txt.text("ready")

      gmeter.root = hu("#gmeter-layer",svg)
      gmeter.circle = hu("#gmeter-circle",gmeter.root)

      dragLayer.root = hu('#drag_layer', svg);
      dragLayer.linelock_light = hu('#linelock_light', dragLayer.root);
      dragLayer.transbrake_light = hu('#transbrake_light', dragLayer.root);
      dragLayer.torque_txt = hu('#text_torque', dragLayer.root);
      dragLayer.power_txt = hu('#text_power', dragLayer.root);

      ready = true;
      updateClock();
      // console.log("rdy")
    }

    function limitVal(min, val,max){
        return Math.min(Math.max(min,val), max);
    }

    function updateAccelerometer(data) {
      //86
      gmeter.circle.css({transform: `translate(${limitVal(-10,data.customModules.accelerationData.xSmooth,10)*8}px, ${-limitVal(-10,data.customModules.accelerationData.ySmooth,10)*8}px`})
      // var roundedGX2 = (data.customModules.accelerationData.xSmooth / 10).toFixed(1);
      // var roundedGY2 = (-data.customModules.accelerationData.ySmooth / 10).toFixed(1);
      // infoDisplay.gXPositive.text(roundedGX2 > 0 ? roundedGX2  : 0)
      // infoDisplay.gXNegative.text(roundedGX2 < 0 ? -roundedGX2 : 0)
      // infoDisplay.gYNegative.text(roundedGY2 > 0 ? roundedGY2  : 0)
      // infoDisplay.gYPositive.text(roundedGY2 < 0 ? -roundedGY2 : 0)
    }

    function updateGagueFuel(data) {
      if (speedoInitialised) {
        data["electrics"]["fuel"]
        //cachedVal.fuel
        let pos = gagues.fuel.path.n.getPointAtLength(data["electrics"]["fuel"] * gagues.fuel.path.n.getTotalLength())
        gagues.fuel.needle.n.style.transform = "translate("+pos.x+"px, "+(pos.y+4)+"px)"
        gagues.fuel.grad.attr({y2: pos.y})
      }
    }

    function updateGagueTemp(data) {
      if (speedoInitialised) {
        let val = (data["electrics"]["watertemp"] - 50) / 80 //min 50C, max 130C
        val = limitVal(0,val,1)
        let pos = gagues.temp.path.n.getPointAtLength(val * gagues.temp.path.n.getTotalLength())
        gagues.temp.needle.n.style.transform = "translate("+pos.x+"px, "+(pos.y-2)+"px)"
        gagues.temp.grad.attr({y2: pos.y})
      }
    }


    // overwriting plain javascript function so we can access from within the controller
    $window.setup = (data) => {
      if(!ready){
        console.log("calling setup while svg not fully loaded");
        setTimeout(function(){ $window.setup(data) }, 100);
        return;
      }

      //console.log("setup",data);
      if(data.uiUnitLength == "metric"){
        speedoDisplay.speedUnit.text("KM/H");
        unitspeedConv = 3.6;
      }
      else{
        speedoDisplay.speedUnit.text("MPH");
        unitspeedConv = 2.23694;
      }
      unitTorque = data.uiUnitTorque;
      unitPower = data.uiUnitPower;
      unitLength = data.uiUnitLength;

      if (data.startupScreen && startupScreen) {
        startupScreen.src = data.startupScreen;
      }
    }

    function setElec(val, state, key){
      if( val === undefined || val === null){console.error("setElec: svg element not found", key); return;}
      if( state === undefined || state === null){console.error("setElec: state not found", key);val.n.style.display = "none"; return;}
      var cssState = (state===true || state>0.1)?"inline":"none";
      val.n.style.display = cssState;
      //val.n.setAttribute("opacity", (state || state>0.1)?1.0:0.3)
    }

    $window.updateElectrics = (data) => {
      // for(var k in electrics.lights){
      //   setElec(electrics.lights[k], data.electrics[k], k);
      // }

      electrics.temp_logo.css({"fill":(data.electrics.watertemp > 110)?"#ef3535":"#fff"});
      electrics.fuel_logo.css({"fill":(data.electrics.lowfuel )?"#ef3535":"#fff"});

      if(cachedVal.dragMode === true){
        dragLayer.linelock_light.css({"fill":(data.electrics.linelock > 0.1)?"#70ff5c":"#000"});
        dragLayer.transbrake_light.css({"stroke":(data.electrics.transbrake > 0.1)?"#ef3535":"#000"});
        if (data.customModules && data.customModules.combustionEngineData){
          let tmp = data.customModules.combustionEngineData.currentTorque;
          if(unitTorque=="imperial"){
            tmp *= 0.7376;
            dragLayer.torque_txt.text(tmp.toFixed()+" lb.ft")
          }
          else{//metric
            dragLayer.torque_txt.text(tmp.toFixed()+" NM")
          }
          tmp = data.customModules.combustionEngineData.currentPower;
          tmp = tmp>0?tmp:0
          switch(unitPower){
            case 'kw':
              tmp *= 0.7355;
              dragLayer.power_txt.text(tmp.toFixed()+" kW")
              break;
            case 'hp':
            case 'bhp':
              dragLayer.power_txt.text(tmp.toFixed()+" HP")
              break;
          }
        }
        else{
          dragLayer.torque_txt.text("err lb.ft")
          dragLayer.power_txt.text("err HP")
        }
      }
      if(data.electrics.odometer){
        let val = data.electrics.odometer
        val *= (unitLength=="metric")?0.001:0.0006215;
        val = Math.min(999999,val);
        electrics.odo_txt.text( val.toFixed(0)+" "+((unitLength=="metric")?"km":"mi") )
      }
    }

    //https://stackoverflow.com/a/56266358
    function isColor(strColor){
      var s = new Option().style;
      s.color = strColor;
      return s.color !== "";
    }

    $window.updateMode = (data) => {
      if(!ready){
        console.log("calling updateMode while svg not fully loaded");
        setTimeout(function(){ $window.updateMode(data) }, 100);
        return;
      }
      //error checking because we can't trust data
      // if(data === null
      // || data === undefined
      // || data.modeName === null
      // || data.modeName === undefined
      // || typeof data.modeName !== "string"
      // || data.modeColor === null
      // || data.modeColor === undefined
      // || typeof data.modeColor !== "string"){
      //   console.error("updateMode receive wrong arguments :", data);
      //   document.getElementById("layer_wip").style.display = "inline";
      //   document.getElementById("tspan995").innerHTML = "MODE";
      //   return;
      // }
      // if(!isColor(data.modeColor)){
      //   console.error("This mode color is not in html format :",data.modeColor)
      //   document.getElementById("layer_wip").style.display = "inline";
      //   document.getElementById("tspan995").innerHTML = "COL";
      //   return;
      // }

      //if you fixed without reload
      // if(document.getElementById("tspan995").innerHTML === "COL"
      // ||document.getElementById("tspan995").innerHTML === "MODE"){
      //   document.getElementById("layer_wip").style.display = "none";
      // }

      //hex color without # works in html but not in svg BECAUSE
      var s = new Option().style;
      s.color = data.modeColor;
      data.modeColor = s.color;

      electrics.mode_txt.text(data.modeName);

      hu('#stop6', svg).css({"stop-color": data.modeColor});

      cachedVal.gForcesVisible = data.modeName.toLowerCase() != "comfort" && data.modeName.toLowerCase() != "savage" && data.modeName.toLowerCase() != "caged";
      cachedVal.dragMode = data.modeName.toLowerCase() == "savage";

      if(cachedVal.gForcesVisible || cachedVal.dragMode || cachedVal.studyHideGauges === true)
        speedoDisplay.rootspeedo.css({display: "none"});
      else
        speedoDisplay.rootspeedo.css({display: "block"});

      if (cachedVal.gForcesVisible === true){
        gmeter.root.css({display: "block"})
      }
      else {
        gmeter.root.css({display: "none"})
      }
      if (cachedVal.dragMode === true){
        dragLayer.root.css({display: "block"});
        speedoDisplay.clockTxt.css({transform: "translateY(117px)"});
      }
      else {
        dragLayer.root.css({display: "none"});
        speedoDisplay.clockTxt.css({transform: ""});
      }
    }

    $window.updateData = (data) => {
      if (data) {
        if(!ready){console.log("not ready");return;}
        // console.log(data);
        //hue = (hue+.5) % 360;
        //setTheme(hue);

        // Update Gear display
        if(isNaN(data.electrics.gear) || data.electrics.gear >= 1)
          speedoDisplay.gear.text(data.electrics.gear)
        else{
          switch(data.electrics.gear){
            case -1:
              speedoDisplay.gear.text("R")
              break;
            case 0:
              speedoDisplay.gear.text("N")
              break;
            default:
              speedoDisplay.gear.text("???")
              break;
          }
        }

        // Update Speed displays (with live toggle for Speed Perception Study)
        var hideGauges = (data.electrics.study_hide_gauges || 0) > 0.5;
        if (cachedVal.studyHideGauges !== hideGauges) {
          cachedVal.studyHideGauges = hideGauges;
          if (hideGauges || cachedVal.gForcesVisible || cachedVal.dragMode) {
            speedoDisplay.rootspeedo.css({display: "none"});
          } else {
            speedoDisplay.rootspeedo.css({display: "block"});
          }
        }
        if (hideGauges) {
          speedoDisplay.speedometerText.text("");
        } else {
          speedoDisplay.speedometerText.text((data.electrics.wheelspeed * unitspeedConv).toFixed());
        }

        updateElectrics(data);
        updateGagueFuel(data);
        updateGagueTemp(data);

        if (data.electrics.ignitionLevel !== lastIgnitionLevel) {
          lastIgnitionLevel = data.electrics.ignitionLevel;
          const gaugesEl = svg.parentNode;
          switch (data.electrics.ignitionLevel) {
            case 0:
              startupScreen.classList.remove("visible");
              gaugesEl.classList.remove("visible");
              break;
            case 1:
              startupScreen.classList.add("visible");
              gaugesEl.classList.remove("visible");
              break;
            case 2:
              startupScreen.classList.remove("visible");
              gaugesEl.classList.add("visible");
              break;
          }
        }

        if (cachedVal.gForcesVisible === true && lastIgnitionLevel === 2) {
          updateAccelerometer(data);
        }
      }
    }
    //ready = true;
    function getRndFloat(min, max) {
      return Math.random() * (max - min) + min;
    }
    function getRndInteger(min, max) {
      return Math.floor(Math.random() * (max - min) ) + min;
    }

    function getRndColor() {
      return "#" + Math.floor(Math.random()*16777215).toString(16);
    }
    var modeIndex = 0;
    var modeArrays = ["demo","savage"];
    function demo(){
      updateMode({modeName:modeArrays[modeIndex], modeColor:"#FFFF00"});
      modeIndex = (modeIndex+1) % modeArrays.length;
      updateData(
        {electrics: {
          lowfuel: Math.random()>0.5, fuel: Math.random(), watertemp: getRndInteger(40,130),
          rpmTacho: getRndInteger(0,60000), maxrpm:10000, oiltemp:getRndInteger(40,130),
          turboBoost:getRndFloat(0,5), engineRunning:Math.random()>0.5,
          signal_L:Math.random(), signal_R:Math.random(), lights:Math.random()*2,
          highbeam:Math.random(), lowpressure:Math.random(), parkingbrake:Math.random(),
          checkengine:Math.random(), gear:"M"+getRndInteger(1,7), wheelspeed: getRndInteger(0,20)/3.6,
          hasABS: getRndInteger(0,2), absActive: Math.random()>0.5, hasESC: getRndInteger(0,2), escActive: Math.random()>0.5,
          hasTCS: getRndInteger(0,2), tcsActive: Math.random()>0.5,
          ignitionLevel: getRndInteger(0,3),
        },
        customModules: {
          accelerationData: {xSmooth:getRndFloat(-20,20) ,ySmooth:getRndFloat(-20,20)},
          environmentData:{time:getRndInteger(0,23)+":"+getRndInteger(0,59), temperatureEnv:Math.random()*100-50},
          dynamicRedlineData:{yellow:12,red:14,shiftLight:false},
          tireData:{
            pressures:{FL:Math.random()*200,FR:Math.random()*200,RL:Math.random()*200,RR:Math.random()*200},
            temperatures:{FL:getRndColor(),FR:getRndColor(),RL:getRndColor(),RR:getRndColor()}
          },
          combustionEngineData:{fuelDisplay:Math.random()*50,averageFuelConsumption:Math.random()*50,currentFuelConsumption:Math.random()*50,remainingRange:Math.random()*200,currentTorque:Math.random()*200,currentPower:Math.random()*200}
        }});
      setTimeout(demo, 2000);
    }
    if(typeof beamng == 'undefined' || typeof beamng.sendActiveObjectLua == 'undefined') { //mode demo only in external browser
      console.log("Demo mode")
      setup({
        fileName: "basic_gauge",
        htmlPath: "local://local/vehicles/bastion/gauges_screen/gauges_standard.html",
        materialName: "@bastion_gauge_screen",
        name: "gauge",
        partName: "bastion",
        partOrigin: "bastion_gauges_basic",
        unit: "metric"})
      setTimeout(()=>{demo()} , 500);
    }
  });

// URL del broker MQTT e topic MQTT
//const broker = 'wss://proxy.marconicloud.it:8884'; // Sostituisci con l'URL del tuo broker MQTT
//const topic = 'radar/misure'; // Sostituisci con il tuo topic MQTT

var boardData = []; // data structure where the measurements sent by the device via MQTT (PUSH mode) are stored
var currBoardId;
var ms;

// List of MQTT brokers to connect to
// the main broker is the preferred broker
// The backup broker is choosen only when the main broker is unavailable
// If the backup broker is active, the main broker is periodically tested and
// selected if again avalilable
// The same behaviour is applied by the IoT device
const brokerUrls = [
    broker1,
    broker2
];

let currentBrokerIndex = 0;
var client = null;

// Function to connect to MQTT broker
function connectToBroker() {
	console.log(currentBrokerIndex);
    const brokerUrl = brokerUrls[currentBrokerIndex];
	
	try{
		client = mqtt.connect(brokerUrl);

		client.on('connect', () => {
		   console.log(`Connected to MQTT broker: ${brokerUrl}`);
		   // Subscribe to topics, publish messages, etc.
		   client.subscribe(pushtopic);
		   client.subscribe(statetopic);
		   alertUser("green");
		});

		client.on('offline', (err) => {
			console.error(`Error with MQTT broker ${brokerUrl}`);
			// Handle error, optionally switch to the next broker
			switchToNextBroker();
			alertUser("red");
		});
		
		client.on('error', (error) => {
			console.error('Errore di connessione MQTT:', error);
			//switchToNextBroker();
			alertUser("red");
		});
		
		client.on('close', () => {
			console.log('Connessione MQTT chiusa');
			switchToNextBroker();
			alertUser("red");
		});
		
		client.on('message', (topic, message) => {
			let data = JSON.parse(message.toString());
			let boardID = data.boardID;
			let r;
			
			console.log('Topic:', topic);
			console.log('Pushtopic:', pushtopic);
			console.log('Statetopic:', statetopic);
			alertUser("green");
			
			if( topic === pushtopic){
				// Verifica se esiste già un elemento per questo boardID
				if (!boardData[boardID]){	
					console.log('New boardID:', boardID);
					boardData[boardID] = {
						radarData: {
							x: [0, 0, 0, 0, 0],
							y: [0, 0, 0, 0, 0],
							rot: 0,
							fw: [0, 0],
							radarmode: 0,
							regions: {
								narea: [1, 2, 3],
								ntarget: [0, 0, 0],
								type: [0, 0, 0],
								x0: [0, 0, 0],
								y0: [0, 0, 0],
								x1: [0, 0, 0],
								y1: [0, 0, 0],
								color: [[255, 0, 0, 127], [0, 255, 0, 127], [0, 0, 255, 127]],
								enabled: [1, 1, 0],
								selected: 0,
								xnr0: [0, 0, 0],
								ynr0: [0, 0, 0],
								xnr1: [0, 0, 0],
								ynr1: [0, 0, 0],
							}
						},
						/*
						radarData: {
							x: [0, 1, 0, 0, 0],
							y: [2, 3, 0, 0, 0],
							rot: 0,
							fw: [0, 0],
							radarmode: 3,
							regions: {
								narea: [1, 2, 3],
								ntarget: [1, 1, 0],
								type: [0, 0, 0],
								x0: [1, 2, 0],
								y0: [4, 5, 0],
								x1: [3, 4, 0],
								y1: [2, 3, 0],
								color: [[255, 0, 0, 127], [0, 255, 0, 127], [0, 0, 255, 127]],
								enabled: [1, 1, 0],
								selected: 0,
								xnr0: [0, 0, 0],
								ynr0: [0, 0, 0],
								xnr1: [0, 0, 0],
								ynr1: [0, 0, 0],
							}
						},
						*/
						tempData: {
							temp: "N/A",
							press: "N/A",
							hum: "N/A",
							gas: "N/A",
						},
						luxData: {
							visible: "N/A",
							infrared: "N/A",
							total: "N/A",
						},
						timestamp: "N/A",
						polltime: 0,
						timer: null,
					};
					// Se non esiste, crea una nuova sezione HTML per questo boardID
					createBoardSection(boardID);
					createCanvasInstances(boardID); // Crea il canvas per questo boardID
					setInputListeners(boardID);
					alertUserIot(boardID, "red");
				}
			}else if(topic === statetopic){	
				console.log('Msg:', data);		
			}
			currBoardId = boardID;
			console.log('CURRENT BOARDID: ', currBoardId);
			//ms = ["measures"];
			ms = ["measures","tempSensor", "luxSensor", "radar", "state"];
			processJson(commandMap, data, [], ms);
		});
	}catch(e){
		console.log('Error try:', e.message);
	}	
}

function getFieldIfExists(obj, field) {
    if (obj && obj.hasOwnProperty(field)) {
        return obj[field];
    }
    return null;
}

// Function to switch to the next MQTT broker
function switchToNextBroker() {
    // Disconnect from the current broker
    if (client) {
        client.end();
        client = null;
    }

    // Move to the next broker in the list
    currentBrokerIndex = (currentBrokerIndex + 1) % brokerUrls.length;

    // Attempt to connect to the next broker
    connectToBroker();
}

// Initial connection attempt
connectToBroker();

// Map of the functions to be executed on a certain path of the received commands (statuses).
// They must coincide with the corresponding paths of the JSON object being transmitted.
// Read-only commands are parameterless and can be invoked in JSON as cells in a command list. For example, with JSON
// "radar": [polltime, servel] 
// but they must be stored as field-value pairs of an object because in JS associative arrays are encoded as objects.
// Write-only commands are parameterized and must be invoked in JSON as field, value pairs. For example, with JSON
// "radar": {
// 	"write":{
// 		polltime: 1
// 		servel: 115200
// 	},
// }
const commandMap = {
	measures: {
		radar: (value) =>{
			console.log('radar ', value);
			let rd = boardData[currBoardId].radarData;
			rd.x = roundArrTo(getFieldIfExists(value,'x'), 2);
			rd.y = roundArrTo(getFieldIfExists(value,'y'), 2);
			rd.regions.ntarget = value.n.map(Number);
			console.log('rd.x ', rd.x);
			console.log('rd.y ', rd.y);
			console.log('rd.regions.ntarget ', rd.regions.ntarget);
			alertUserIot(currBoardId, "green");
			if(boardData[currBoardId].timer){
				boardData[currBoardId].timer.start();
			}
		},
		tempSensor: (value) =>{
			console.log('tempSensor ', value);
			boardData[currBoardId].tempData = {
				temp: roundTo(getFieldIfExists(value,'temp'), 2),
				press: roundTo(getFieldIfExists(value,'press'), 1),
				hum: roundTo(getFieldIfExists(value,'hum'), 2),
				gas: roundTo(getFieldIfExists(value,'gas'), 1),
			}
			let sensorDataElement = document.querySelector(`#sensorData-${currBoardId}`);
			sensorDataElement.querySelector('.temp').innerText = `${boardData[currBoardId].tempData.temp} °C`;
			sensorDataElement.querySelector('.press').innerText = `${boardData[currBoardId].tempData.press} Pa`;
			sensorDataElement.querySelector('.hum').innerText = `${boardData[currBoardId].tempData.hum} %`;
			sensorDataElement.querySelector('.gas').innerText = `${boardData[currBoardId].tempData.gas}`;
		},
		luxSensor: (value) =>{
			console.log('luxSensor ', value);
			boardData[currBoardId].luxData = {
				visible: roundTo(getFieldIfExists(value,'visible'), 4),
				infrared: roundTo(getFieldIfExists(value,'infrared'), 4),
				total: roundTo(getFieldIfExists(value,'total'), 4)
			}
			let sensorDataElement = document.querySelector(`#sensorData-${currBoardId}`);
			sensorDataElement.querySelector('.visible').innerText = `${boardData[currBoardId].luxData.visible} Lux`;
			sensorDataElement.querySelector('.infrared').innerText = `${boardData[currBoardId].luxData.infrared} Lux`;
			sensorDataElement.querySelector('.total').innerText = `${boardData[currBoardId].luxData.total} Lux`;
		}
	},
	state: {
		fw: (value) => {
				console.log('Setting fw to', value);
				boardData[currBoardId].fw = value;
				let timestampElement = document.querySelector(`#timestamp-${currBoardId}`);
				timestampElement.innerText = boardData[currBoardId].timestamp + "   -   FW version: " + boardData[currBoardId].fw;
			},
		polltime: (value) => {
				console.log('Setting pollTime to', value);
				boardData[currBoardId].polltime = Number(value);
				if(!boardData[currBoardId].timer){
					boardData[currBoardId].timer = new MonostableTimer(boardData[currBoardId].polltime*2, ()=>{
						let iotmsg = document.getElementById(`iotmsg-${currBoardId}`);
						iotmsg.style.backgroundColor = "red";
						iotmsg.style.color = "white";
						iotmsg.value = "Iot OFF";
					});
				}
				setElem(currBoardId, "poll1", millisToTimeString(value), '.poll1');
			},
		servel: (value) => {
				console.log('Setting servel to', value);
				setElem(currBoardId, "servel", value, '.servel');
			},
		radarmode: (value) => {
			console.log('Setting radarMode to', value)
			setElem(currBoardId, "radarmode", value, '.sel');
		},
		radafactory: () => {
			console.log('Restoring radar');
			setElem(currBoardId, "radafactory", "Invia");
		},
		radarstate: (value) => {
			console.log('radarstate receive');
			setElem(currBoardId, "radarstate", value,'.rep');
		},
		regions: (value) => {
			console.log('regions receive ', value);
			console.log('currBoardId ', currBoardId);
			console.log('currregion ', boardData[currBoardId].radarData);
			// update boardData region from state feedback
			let r = boardData[currBoardId].radarData.regions;
			r.x0 = value.x0.map(Number);
			r.y0 = value.y0.map(Number);
			r.x1 = value.x1.map(Number);
			r.y1 = value.y1.map(Number);
			r.narea = value.narea.map(Number);
			r.type = value.type.map(Number);
			r.enabled = value.enabled.map(Number);

			console.log('regions receive ENABLED', r.enabled);
			setElem(currBoardId, "areaenable", '', '');
			setElem(currBoardId, "areatypesel", '', '');
			setElem(currBoardId, "areavertices", '', '');
			setElem(currBoardId, "areasel", '', '');
			expandBoardDataRegion(currBoardId);
			updateInputsFromBoardDataRegion(currBoardId);
			updateBoardUI(currBoardId);
		},
		ntarget: (value) => {
			console.log('ntarget receive');
			boardData[currBoardId].regions.ntarget = value;
			console.log('ntarget'+value);
			//setElem("bho", value,'.rep');
		},
	},
	timestamp: (val) => {
		boardData[currBoardId].timestamp = convertDateTimeToHumanReadable(val);
		let timestampElement = document.querySelector(`#timestamp-${currBoardId}`);
		timestampElement.innerText = boardData[currBoardId].timestamp + "   -   FW version: " + boardData[currBoardId].fw;
	},
	boardID: (val) => {
		console.log('boardID');
		let elem = document.getElementById(`sensorData-${currBoardId}`);
		let inputelem = elem.querySelector('.boardID');
		inputelem.innerHTML = val;
	},
};


// Sends, via a JSON, the command to perform configuration settings on the IoT device in a PUSH mode.
// These are commands with parameters that call functions with arguments.
function pubAtt(att, val, bId, type) {// type: write, read
	//const timestamp = getTimestamp();
	const message = JSON.stringify({
		boardID: bId,
		config: {
			[type]: {// comandi con parametri
				[att]: val, // coppia nome_comando, parametro_comando
			}
		},
	});
	client.publish(cmdtopic, message, (error) => {
		if (error) {
			console.error('Errore nella pubblicazione:', error);
		} else {
			console.log('Messaggio pubblicato:', message);
		}
	});
}

// Sends, via a JSON, the command to execute the request, in a PULL mode, for status information on the IoT device.
// These are commands without parameters that call functions without arguments encoded in the JSON as a list of names in an array.
function pubReadAtt(bId, att) {// type: write, read
	//const timestamp = getTimestamp();
	const message = JSON.stringify({
		boardID: bId,
		config: {
			read:[att],//list of read only commands without parameters
			}
	});
	client.publish(cmdtopic, message, (error) => {
		if (error) {
			console.error('Errore nella pubblicazione:', error);
		} else {
			console.log('Messaggio pubblicato:', message);
		}
	});
}

// Funzione per arrotondare ciascun valore a un numero specificato di cifre decimali
function roundArrTo(array, decimals, div=1) {
	if (array != null){
		const factor = Math.pow(10, decimals);
		return array.map(val => Math.round(val * factor/div) / factor);
	}else{
		return null;
	}
}

function roundTo(val, decimals) {
	if (val != null){
		const factor = Math.pow(10, decimals);
		return Math.round(val * factor) / factor;
	}else{
		return 0;
	}
}

function capitalizeFirstLetter(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
}

// Identifies, in the web interface, the value fields of the objects modified by a command.
// Reports the value actually set on the device obtained from the feedback channel via MQTT
function setElem(boardID, type, val, target='.send'){
	console.log('boardID', boardID);
	console.log('type', type);
	console.log('val', val);
	console.log('str', `${type}-${boardID}`);
	let elem = document.getElementById(`${type}-${boardID}`);
	elem.style.backgroundColor = "#ffffff"; // resets the wait signal for command feedback
	if(target != ''){
		let inputelem = elem.querySelector(target);
		inputelem.value = val;
	}
}

// Recursive parser of JSON data received asynchronously (representing the state of the device) 
// Returns the path of the command in the received JSON data structure. 
// The path must correspond to the path of the function to be called in the data structure of the command map. 
// Invokes the function which, in the command map, has its pointer on that path.
function processJson(commandMap, jsonObj, basePath = [], measures = []) {
	let measure = false;
	if(measures.includes(basePath[basePath.length-1])){
		measure = true;
	}

    for (const key in jsonObj) {
        if (jsonObj.hasOwnProperty(key)) {
            const value = jsonObj[key];
            const currentPath = [...basePath, key];
            if (typeof value === 'object' && !Array.isArray(value) && !measure) {
				processJson(commandMap, value, currentPath, measures);          
            } else if (Array.isArray(value)) {// if it is a list of functions without parameters
                for (const item of value) {
                    executeCommand(commandMap, [...currentPath, item]);
                }
            } else {// if it is a primitive value, the field (key, value) corresponding to the pair (function name, list of function parameters)
                executeCommand(commandMap, currentPath, value); // value is a primitive value 
            }
        }
    }
}

// Function that retrieves and invoke the function at the command path
function executeCommand(commandMap, commandPath, parameters = null) {
    let currentLevel = commandMap;
    for (const key of commandPath) {
        if (currentLevel[key]) {
            currentLevel = currentLevel[key];
        } else {
            console.error(`Unknown command: ${commandPath.join('/')}`);
            return;
        }
    }

    if (typeof currentLevel === 'function') {
        if (parameters !== null) {
            currentLevel(parameters);
        } else {
            currentLevel();
        }
    } else {
        console.error(`Final command is not a function: ${commandPath.join('/')}`);
    }
}

function millisToTimeString(millis) {
    let hours = Math.floor(millis / (1000 * 60 * 60));
    let minutes = Math.floor((millis % (1000 * 60 * 60)) / (1000 * 60));
    let seconds = Math.floor((millis % (1000 * 60)) / 1000);

    // Aggiungi uno zero davanti ai numeri minori di 10
    hours = hours < 10 ? '0' + hours : hours;
    minutes = minutes < 10 ? '0' + minutes : minutes;
    seconds = seconds < 10 ? '0' + seconds : seconds;

    return `${hours}:${minutes}:${seconds}`;
}
						
// Disegna la griglia delle aree
function drawRegions(sketch, bid) {
    //stroke(255);
    sketch.strokeWeight(1);
	
	let r = boardData[bid].radarData.regions;
	
	// draw areas rectangles
	for(i=0; i<3; i++){
		//console.log("r.enabled: "+ r);
		if(r.enabled[i]){
			//console.log("r: "+[r.x0[i], r.y0[i], r.x1[i], r.y1[i]]);
			if(boardData.radarData.rot){// calcola il passaggio dei vertici dal riferimento ruotato al non ruotato
				// Scala i valori per adattarli allo schermo
				//console.log("r: "+[r.xr0[i], r.yr0[i], r.xr1[i], r.yr1[i]]);
				scaledX0 = -r.xnr0[i];
				scaledY0 = height - r.ynr0[i];
				scaledX1 = -r.xnr1[i]
				scaledY1 = height - r.ynr1[i];
			}else{// lascia i vertici nel riferimento NON ruotato
				//console.log("r: "+[r.xnr0[i], r.ynr0[i], r.xnr1[i], r.ynr1[i]]);
				scaledX0 = r.xnr0[i];
				scaledY0 = r.ynr0[i];
				scaledX1 = r.xnr1[i];
				scaledY1 = r.ynr1[i];
			}
			//fill(r.color || [255, 0, 0]);
			noFill();
			stroke(r.color[i]);
			rectMode(CORNERS);
			
			//console.log("rect: "+[scaledX0, scaledY0, scaledX1, scaledY1]);
			let x = scaledX0; // Minimo tra le coordinate X per ottenere il lato sinistro
			let y = scaledY0; // Minimo tra le coordinate Y per ottenere il lato superiore
			
			// Disegna il punto
			//fill(0, 255, 0);
		
			sketch.ellipse(scaledX0, -scaledY0, 5, 5);

			sketch.ellipse(scaledX1, -scaledY1, 5, 5);

			if (r.ntarget[i]==1) {
				// Imposta il colore di riempimento a rosso con trasparenza (alpha)
				fill(r.color[i]);  // Rosso semitrasparente (alpha=127 su 255)
			} else {
				// Imposta un colore di riempimento predefinito (ad esempio bianco)
				noFill();
			}
			// Ora, ricorda che l'asse Y è invertito con la nuova origine
			sketch.rect(x, -y, scaledX1, -scaledY1); // Disegna il rettangolo
			// Etichette
		}
	}
}

// Disegna la griglia tachimetrica
function drawGrid(sketch) {
    sketch.stroke(100);
    sketch.strokeWeight(0.5);

    // Linee verticali
    for (let x = -sketch.width * 0.3 * 2; x <= sketch.width * 0.3 * 2; x += sketch.width * 0.05) {
        sketch.line(x, -sketch.height, x, 0);
    }

    // Linee orizzontali
    for (let y = 0; y >= -sketch.height; y -= sketch.height * 0.05) {
        sketch.line(-sketch.width * 0.3 * 2, y, sketch.width * 0.3 * 2, y);
    }
}

function drawDistanceCircles(sketch, bid) {
    const maxDistance = 10; // La distanza massima del radar
    const numCircles = 5; // Numero di cerchi da disegnare
	
	let radarData = boardData[bid].radarData;

	for (let i = 1; i <= numCircles; i++) {
        let radius = sketch.map(i, 0, numCircles, 0, sketch.width / 2);
		if(!radarData.rot){
			sketch.ellipse(0, 0, radius * 2, radius * 2);
		}else{
			sketch.ellipse(0, -sketch.height, radius * 2, radius * 2);
		}
        
        // Etichette di distanza
        sketch.textSize(12);
        sketch.textAlign(sketch.CENTER);
        let rounded = Math.round((maxDistance / numCircles) * i * 10) / 10;
        sketch.text(`${rounded} m`, radius-13, -5 + radarData.rot*(20 - sketch.height));
    }
}

// Create the dashboard of measurements and commands
function createBoardSection(boardID) {
    let gridContainer = document.querySelector('.grid-container');

	const tmpl1 = document.createElement("template");
	tmpl1.innerHTML = `<div class='col-12 col-s-12' id='txt-banner'  class="header">
	<h2 class="header">Monitoraggio radar</h2></div>
	<div class='col-12 col-s-12' id="timestamp-${boardID}"></div>
	<div class='col-9 col-s-12 boxed' id='radar-${boardID}'></div>
	<div class='col-3 col-s-12 boxed' id='sensorData-${boardID}'>
		<p>Board ID: <span class="boardID">${boardID}</span></p>
		<p>Temperatura: <span class="temp">N/A</span></p>
		<p>Pressione: <span class="press">N/A</span></p>
		<p>Umidità: <span class="hum">N/A</span></p>
		<p>Gas: <span class="gas">N/A</span></p>
		<p>Luce visibile: <span class="visible">N/A</span></p>
		<p>Luce infrarossa: <span class="infrared">N/A</span></p>
		<p>Luce totale: <span class="total">N/A</span></p>
	</div>
			
	<div id='poll1-${boardID}' class='col-1 col-s-12'>
		<div class="txt"><p >Polling time</p></div>
		<input class="poll1 button-large" type="time" step="1" />
		<input class="send button-small button-blue" type="button" value="Invia"/>
	</div>
	<div class='col-1 col-s-12' id='servel-${boardID}'>
		<div class="txt"><p >Radar serial</p></div>
		<select name="vels" class="servel button-large">
			<option value="9600">9600</option>
			<option value="19200">19200</option>
			<option value="38400">38400</option>
			<option value="57600">57600</option>
			<option value="115200">115200</option>
			<option value="230400">230400</option>
			<option value="256000">256000</option>
			<option value="460800">460800</option>
		</select>
		<input class="send button-small button-blue" type="button" value="Invia"/>
	</div>
	<div class='col-1 col-s-12' id='radarstate-${boardID}'>
		<div class="txt"><p >Radar state</p></div>
		<input type="text"  value="0" class="rep">
		<input type="button" class="send button-blue" value="Invia">
	</div>
	<div class='col-1 col-s-12' id='radarfactory-${boardID}'>
		<div class="txt"><p >Radar factory</p></div>
		<input type="text"  value="0" class="rep">
		<input type="button" class="send button-blue" value="Invia">
	</div>
	<div class='col-1 col-s-12' id='radarmode-${boardID}'>
		<div class="txt"><p >Radar mode</p></div>
		<select name="target" class="sel button-large">
			<option value="1">Track</option>
			<option value="2">Report</option>
			<option value="3">Both</option>
		</select>
		<input type="button" class="send button-blue" value="Invia">
	</div>	
	<div class='col-1 col-s-12' id='areaenable-${boardID}'>
		<div class="txt"><p class="txt">Stato area</p></div>
		<select name="areaenable" class="sel button-large">
			<option value="1">Enabled</option>
			<option value="0">Disabled</option>
		</select>
		<input type="button" class="send button-blue" value="Invia">
	</div> 
	<div class='col-1 col-s-12' id='areatypesel-${boardID}'>
		<div class="txt"><p >Tipo area</p></div>
		<select name="areatype" class="sel button-large">
			<option value="0">Monitor</option>
			<option value="1">Filter</option>
		</select>
		<div><input id='iotmsg-${boardID}' class="iotmsg button-text" type="text" value="IoT OFF"/></div>
	</div>
	<div class='col-2 col-s-12' id='areavertices-${boardID}'>
		<div class="txt"><p >Vertici area</p></div>
		<div class="button-container">
			<label class="poll1 button-small">V1</label> 
			<label class="poll1 button-small">V2</label> 
		</div>
		<div class="button-container">
			<input class="poll1 button-small x0" type="text" />
			<input class="poll1 button-small y0" type="text" />
			<input class="poll1 button-small x1" type="text" />
			<input class="poll1 button-small y1" type="text"/>
		</div>
		<div class="button-container" id='connstatel'>
			<input id='connmsg-${boardID}' class="connmsg button-text" type="text" value="MQTT OFF"/>
		</div>
	</div>
	<div class='col-1 col-s-12' id='areasel-${boardID}'>
		<div class="txt"><p>Seleziona area</p></div>
			<select name="target" class="sel button-large">
				<option value="1">Area 1</option>
				<option value="2">Area 2</option>
				<option value="3">Area 3</option>
			</select>
			<input class="send button-small button-blue" type="button" value="Invia"/>
	</div>
	<div class='col-1 col-s-12' id='areareset-${boardID}'>
		<div class="txt"><p >Cancella tutte</p></div>
		<input type="text"  value="0">
		<input type="button" class="send button-blue" value="Invia">
	</div>		
	<div class='col-1 col-s-12' id='radarinvert-${boardID}'>
		<p>Inverti griglia</p>
		<input type="text"  class="txt"value="0">
		<input type="button"  class="send button-blue" value="Invia">
	</div> `
	
	var body = tmpl1.content.cloneNode(true);

	const tmpl2 = document.createElement("template");
	tmpl2.innerHTML = `<div class='col-12 col-s-12' id='txt-nulla' class='footer'><h2 class="footer">Monitoraggio radar</h2></div>`
	var footer = tmpl2.content.cloneNode(true);

	gridContainer.appendChild(body);
	gridContainer.appendChild(footer);
	pubReadAtt(boardID, "allstate");
}

// Bind command listeners to input elements 
function setInputListeners(boardID) {
    let poll1div = document.getElementById(`poll1-${boardID}`);// Trova l'id del contenitore grid degli input
	let poll1send = poll1div.querySelector('.send');// Trova la classe dell'oggetto di input che riceve l'evento utente
	let poll1val = poll1div.querySelector('.poll1');// Trova la classe dell'oggetto di input da leggere ogni evento utente
	/// POLL TIME SETTING  ///////////////////////////////////////////////////////////////////////////////////////
	poll1send.onclick = () => {
		const timeValue = poll1val.value;
		console.log('timeValue:', timeValue);
		// Dividi il valore in ore, minuti e secondi
		const [hours, minutes, seconds] = timeValue.split(':').map(Number);
		// Calcola i millisecondi
		const milliseconds = ((hours * 3600) + (minutes * 60) + seconds) * 1000;
		pubAtt("polltime", milliseconds, boardID, "write");
		poll1div.style.backgroundColor = "#E67E22"; // activate the wait signal for command feedback
	}
	/// RADAR SERIAL VEL SETTING ///////////////////////////////////////////////////////////////////////////////////////
	let servel = document.getElementById(`servel-${boardID}`);// Trova l'id del contenitore grid degli input
	let servelsend = servel.querySelector('.send');// Trova la classe dell'oggetto di input che riceve l'evento utente
	let servelval = servel.querySelector('.servel');// Trova la classe dell'oggetto di input da leggere ogni evento utente
	servelsend.onclick = () => {
		const serValue = servelval.value;	
		console.log('serValue', serValue);
		pubAtt("servel", serValue, boardID, "write");
		servel.style.backgroundColor = "#E67E22"; // activate the wait signal for command feedback
	}
	/// RADAR MODE  ///////////////////////////////////////////////////////////////////////////////////////
	let radarmode = document.getElementById(`radarmode-${boardID}`);// Trova l'id del contenitore grid degli input
	let radarmodesel = radarmode.querySelector('.sel');
	let radarmodesend = radarmode.querySelector('.send');// Trova la classe dell'oggetto di input che riceve l'evento utente
	radarmodesend.onclick = () => {
		val = radarmodesel.value;
		pubAtt("radarmode", val, boardID, "write");
		radarmode.style.backgroundColor = "#E67E22"; // activate the wait signal for command feedback	
	}
	/// RADAR AREA FACTORY  ///////////////////////////////////////////////////////////////////////////////////////
	let radarfactory = document.getElementById(`radarfactory-${boardID}`);// Trova l'id del contenitore grid degli input
	let radafactorysend = radarfactory.querySelector('.send');// Trova la classe dell'oggetto di input che riceve l'evento utente
	radafactorysend.onclick = () => {
		pubAtt("radarfactory", "1", boardID, "write");
		radarfactory.style.backgroundColor = "#E67E22"; // activate the wait signal for command feedback
	}
	/// RADAR STATE ON/OFF  ///////////////////////////////////////////////////////////////////////////////////////
	let radarstate = document.getElementById(`radarstate-${boardID}`);// Trova l'id del contenitore grid degli input
	let radarstatesend = radarstate.querySelector('.send');// Trova la classe dell'oggetto di input che riceve l'evento utente
	radarstatesend.onclick = () => {
		pubAtt("radartoggle", "1", boardID, "write");
		radarstate.style.backgroundColor = "#E67E22"; // activate the wait signal for command feedback
	}
	/// RADAR AREA CONFIG  ///////////////////////////////////////////////////////////////////////////////////////
	let areavertices = document.getElementById(`areavertices-${boardID}`);
	let x0= areavertices.querySelector('.x0');// Trova la classe dell'oggetto di input da leggere ogni evento utente
	let y0= areavertices.querySelector('.y0');
	let x1= areavertices.querySelector('.x1');
	let y1= areavertices.querySelector('.y1');
	let areatypesel = document.getElementById(`areatypesel-${boardID}`);// Trova l'id del contenitore grid degli inputlet areavertices = document.getElementById('areavertices');// Trova l'id del contenitore grid degli input
	let areaenable = document.getElementById(`areaenable-${boardID}`);// Trova l'id del contenitore grid degli input
	let areaenablesel = areaenable.querySelector('.sel');
	let areatypeselsel = areatypesel.querySelector('.sel');
	dataentry = [x0, y0, x1, y1, areaenablesel, areatypeselsel];

	let areasel = document.getElementById(`areasel-${boardID}`);
	let areaselsend = areasel.querySelector('.send');// Trova la classe dell'oggetto di input che riceve l'evento utente
	areaselsend.onclick = () => {
		// update boardData region from user input
		let r = boardData[currBoardId].radarData.regions;
		let selectedRectangle = r.selected-1;
		let typeval= areatypeselsel.value;
		//let i= areaselsel.value;
		let enabledval = areaenablesel.value;
		//boardData.radarData.regions.selected = i;
		r.x0[selectedRectangle] = Number(x0.value);
		r.y0[selectedRectangle] = Number(y0.value);
		r.x1[selectedRectangle] = Number(x1.value);
		r.y1[selectedRectangle] = Number(y1.value);
		r.type[selectedRectangle] = Number(typeval);
		r.enabled[selectedRectangle] = Number(enabledval);
		r.narea[selectedRectangle] = Number(selectedRectangle);
		//expandBoardDataRegion();		

		const region = {	
			narea: boardData[currBoardId].radarData.regions.selected,
			type: typeval,
			enabled: enabledval,
			x0: x0.value,
			y0: y0.value,
			x1: x1.value,
			y1: y1.value,
		};			
		console.log('region send', region);
		pubAtt("region", region, boardID, "write"); //serializza e invia
		areavertices.style.backgroundColor = "#E67E22"; // activate the wait signal for command feedback
		areasel.style.backgroundColor = "#E67E22"; // activate the wait signal for command feedback
		areatypesel.style.backgroundColor = "#E67E22"; // activate the wait signal for command feedback
	}
	/// RADAR AREA ENABLE/DISABLE  ///////////////////////////////////////////////////////////////////////////////////////
	let areaselsel = areasel.querySelector('.sel');
	areaselsel.onchange = () => {
		console.log("areaselsel.onchange: "+ areaselsel.value);
		boardData[currBoardId].radarData.regions.selected = Number(areaselsel.value);
		updateInputsFromBoardDataRegion(currBoardId);
	}
	/// RADAR AREA ENABLE/DISABLE  ///////////////////////////////////////////////////////////////////////////////////////
	let areaenablesend = areaenable.querySelector('.send');
	areaenablesend.onclick = () => {
		let areaenable = document.getElementById(`areaenable-${boardID}`);
		let areaenablesel = areaenable.querySelector('.sel');
		let enabled = Number(areaenablesel.value);
		
		let r = boardData[currBoardId].radarData.regions;
		let region = r.selected;
		if(enabled){
			console.log('areenable '+region);
			r.enabled[region-1] = 1;
			pubAtt("areaenable", region, boardID, "write"); //serializza e invia
		}else{
			console.log('areadisable '+region);
			r.enabled[region-1] = 0;
			pubAtt("areadisable", region, boardID, "write"); //serializza e invia
		}
		areaenable.style.backgroundColor = "#E67E22"; // activate the wait signal for command feedback
	}
	/// RADAR GRID INVERT ///////////////////////////////////////////////////////////////////////////////////////
	let radarinvert = document.getElementById(`radarinvert-${boardID}`);// Trova l'id del contenitore grid degli input
	let radarinvertsend = radarinvert.querySelector('.send');// Trova la classe dell'oggetto di input che riceve l'evento utente
	let radarinvertxt = radarinvert.querySelector('.txt');
	radarinvertsend.onclick = () => {
		if(boardData[currBoardId].radarData.rot == 0){
			boardData[currBoardId].radarData.rot = 1;
			radarinvertxt.value = "Ruotata";
		}else{
			boardData[currBoardId].radarData.rot = 0;
			radarinvertxt.value = "Non ruotata";
		}
	}
	/// RADAR ALL AREAS RESET ///////////////////////////////////////////////////////////////////////////////////////
	let areareset = document.getElementById(`areareset-${boardID}`);// Trova l'id del contenitore grid degli input
	let arearesetsend = areareset.querySelector('.send');// Trova la classe dell'oggetto di input che riceve l'evento utente
	arearesetsend.onclick = () => {
		console.log('areareset');
		pubAtt("areareset", 1, boardID, "write"); //serializza e invia
		areareset.style.backgroundColor = "#E67E22"; // activate the wait signal for command feedback
	}
}

function alertUser(color){
	// Seleziona tutti gli elementi con la classe 'msg'
    var msglist = document.querySelectorAll(".connmsg");

    // Itera su tutti gli elementi selezionati e imposta lo sfondo giallo
    msglist.forEach(function(elem) {
        elem.style.backgroundColor = color;
		elem.style.color = "white";
		if(color=="green"){
			elem.value = "MQTT ON";
		}else{
			elem.value = "MQTT OFF";
		}
    });
}

function alertUserIot(boardID, color){
	let iotmsg = document.getElementById(`iotmsg-${boardID}`);
	iotmsg.style.backgroundColor = color;
	iotmsg.style.color = "white";
	if(color=="green"){
		iotmsg.value = "Iot ON";
	}else{
		iotmsg.value = "Iot OFF";
	}
}

// Definisci la classe MonostableTimer
class MonostableTimer {
	constructor(timeoutDuration, callback) {
		this.timeoutDuration = timeoutDuration;  // Durata del timer in millisecondi
		this.callback = callback;  // Funzione da eseguire al termine del timer
		// this.callback = callback.bind(this);
		this.timeoutId = null;  // ID del timeout
	}

	// Avvia o resetta il timer
	start() {
		// Se esiste un timer attivo, resettalo
		if (this.timeoutId) {
			clearTimeout(this.timeoutId);
			console.log("Timer resettato");
		}

		// Imposta un nuovo timer
		this.timeoutId = setTimeout(() => {
			// Verifica che la callback sia una funzione prima di chiamarla
			if (typeof this.callback === 'function') {
				this.callback();  // Esegue la callback
			} else {
				console.error("Callback non è una funzione!");
			}
		}, this.timeoutDuration);

		console.log("Timer avviato per " + this.timeoutDuration + " millisecondi.");
	}

	// Ferma il timer (se necessario)
	stop() {
		if (this.timeoutId) {
			clearTimeout(this.timeoutId);
			console.log("Timer fermato");
		}
		this.timeoutId = null;
	}
}

// Massive update of measurement outputs
// is used for the massive update of all measurements
function updateBoardUI(boardID) {
   
    let timestampElement = document.getElementById(`timestamp-${boardID}`);
    timestampElement.innerText = convertDateTimeToHumanReadable(boardData[boardID].timestamp) + "   -   FW version: " + boardData[boardID].fw;

    let sensorDataElement = document.getElementById(`sensorData-${boardID}`);
    sensorDataElement.querySelector('.temp').innerText = `${boardData[boardID].tempData.temp} °C`;
    sensorDataElement.querySelector('.press').innerText = `${boardData[boardID].tempData.press} Pa`;
    sensorDataElement.querySelector('.hum').innerText = `${boardData[boardID].tempData.hum} %`;
    sensorDataElement.querySelector('.gas').innerText = `${boardData[boardID].tempData.gas}`;
    sensorDataElement.querySelector('.visible').innerText = `${boardData[boardID].luxData.visible} Lux`;
    sensorDataElement.querySelector('.infrared').innerText = `${boardData[boardID].luxData.infrared} Lux`;
    sensorDataElement.querySelector('.total').innerText = `${boardData[boardID].luxData.total} Lux`;
}

function expandBoardDataRegion(boardID) {	
	let r = boardData[boardID].radarData.regions;
	//let selectedRectangle = r.selected-1;

	let container1 = document.getElementById(`radar-${boardID}`);
	let width1 = container1.offsetWidth*0.988;
	let height1 = width1*1.2/2;
	for(let i=0; i<3; i++){
		// rotated
		selectedRectangle = i;
		r.xnr0[selectedRectangle] = map(r.x0[selectedRectangle], -6, 6, -width1 * 0.3, width1 * 0.3);
		r.ynr0[selectedRectangle] = map(r.y0[selectedRectangle], 0, -6, 0, -height1);
		r.xnr1[selectedRectangle] = map(r.x1[selectedRectangle], -6, 6, -width1 * 0.3, width1 * 0.3);
		r.ynr1[selectedRectangle] = map(r.y1[selectedRectangle  ], 0, -6, 0, -height1);

		r.xr0[selectedRectangle] = -r.xnr0[selectedRectangle];
		r.yr0[selectedRectangle] = height1 - r.ynr0[selectedRectangle];
		r.xr1[selectedRectangle] = -r.xnr1[selectedRectangle];
		r.yr1[selectedRectangle] = height1 - r.ynr1[selectedRectangle];
		
		console.log("r.xnr0[i]:"+r.xnr0[selectedRectangle]);
		console.log("r.ynr0[i] :"+r.ynr0[selectedRectangle]);
		console.log("r.xnr1[i] :"+r.xnr1[selectedRectangle]);
	}
	console.log("r.ynr1[i] :"+r.ynr1[selectedRectangle]);
}

// Creazione funzione di setup e loop di disegno di ogni canvas
function createCanvasInstances(boardID) {
    new p5(function(sketch) {
        let canvas;
		let dragging = false;
		let resizing = false;
		let offsetX = 0;
		let offsetY = 0;
		let selectedCorner = null;
		let width;
		let height;

		// Utility to check if mouse is near a corner for resizing
		function isNearCorner(mx, my, x, y, threshold) {
			let d = sketch.dist(mx, my, x, y);
			console.log("Dist: "+d);
			return d  < threshold;
		}

        sketch.setup = function() {
            let container = document.getElementById(`radar-${boardID}`);
            let width = container.offsetWidth * 0.988;
            let height = width * 1.2 / 2;
			console.log("width: "+width);
			console.log("height: "+height);

            let canvas = sketch.createCanvas(width, height).parent(container);
        };
    
        sketch.draw = function() {
            sketch.background(0);
            sketch.translate(sketch.width / 2, sketch.height); // Sposta l'origine in basso al centro
            drawGrid(sketch);
			drawRegions(sketch, boardID);
            sketch.stroke(255);
            sketch.noFill();
            drawDistanceCircles(sketch, boardID);
			let x = 0;
			let y = 0;
			let scaledX = 0;
			let scaledY = 0;

            let radarData = boardData[boardID].radarData;
			if(radarData.x){
				for (let i = 0; i < radarData.x.length; i++) {
					x = Number(radarData.x[i]);
					y = Number(radarData.y[i]);

					if(radarData.rot){
						// Scala i valori per adattarli allo schermo
						scaledX = sketch.map(x, 6, -6, -sketch.width * 0.3, sketch.width * 0.3);
						scaledY = sketch.map(y, 6, 0, 0, -height);
					}else{
						scaledX = sketch.map(x, -6, 6, -sketch.width * 0.3, sketch.width * 0.3);
						scaledY = sketch.map(y, 0, 6, 0, -sketch.height);
					}
					// Disegna il punto
					sketch.fill(0, 255, 0);
					sketch.noStroke();        
					sketch.ellipse(scaledX, scaledY, 10, 10);
					// Etichette
					sketch.fill(255);
					sketch.textSize(12);
					sketch.text(`X: ${x}`, scaledX + 5, scaledY - 20+radarData.rot*20);
					sketch.text(`Y: ${y}`, scaledX + 5, scaledY - 10+radarData.rot*20);
				}
			}
        };
        
        sketch.windowResized = function () {
            let container = document.getElementById(`radar-${boardID}`);
            let width = container.offsetWidth * 0.988;
            let height = width * 1.1 / 2;

            sketch.resizeCanvas(width, height);
        };

		sketch.mousePressed = function() {
			let scaledX = 0;
			let scaledY = 0;
			let r = boardData.radarData.regions;
			let selectedRectangle = r.selected -1;
			let rect = [];	
			
			scaledX = mouseX - width /2;
			scaledY = height - mouseY;
			
			if(boardData.radarData.rot){
				// calcola il passaggio dei vertici dal riferimento ruotato al non ruotato
				rect[0] = -r.xnr0[selectedRectangle];
				rect[1] = height - r.ynr0[selectedRectangle];
				rect[2] = -r.xnr1[selectedRectangle];
				rect[3] = height - r.ynr1[selectedRectangle];
				console.log("rect rot----------------------------");
			}else{		
				rect[0] = r.xnr0[selectedRectangle];
				rect[1] = r.ynr0[selectedRectangle];
				rect[2] = r.xnr1[selectedRectangle];
				rect[3] = r.ynr1[selectedRectangle];
				// Scala i valori del mouse per adattarli al riferimento dello schermo!!!
				console.log("rect no rot----------------------------");
			}
			
			///---------CALCOLO NEL RIFERIMENTO NON RUOTATO--------------------------
			console.log("mousePressed----------------------------");
			console.log("rect: "+rect);
			console.log("scaledX-rect[0]: "+scaledX+"-"+rect[0]);
			console.log("scaledY- rect[1]: "+scaledY+"-"+rect[1]);
			// Check if mouse is near any corner for resizing
			const resizeThreshold = 10;
			let inside1 = scaledX > rect[0] && scaledX < rect[2] && scaledY > rect[3] && scaledY < rect[1];
			let inside2 = scaledX > rect[2] && scaledX < rect[0] && scaledY > rect[1] && scaledY < rect[3];
			if (isNearCorner(scaledX, scaledY, rect[0], rect[1], resizeThreshold)) {
				dragging = false;
				resizing = true;
				selectedCorner = 'topLeft';
				console.log("Near topleft");
			} else if (isNearCorner(scaledX, scaledY, rect[2], rect[1], resizeThreshold)) {
				dragging = false;
				resizing = true;
				selectedCorner = 'topRight';
				console.log("Near topRight");
			} else if (isNearCorner(scaledX, scaledY, rect[0], rect[3], resizeThreshold)) {
				dragging = false;
				resizing = true;
				selectedCorner = 'bottomLeft';
				console.log("Near bottomLeft");
			} else if (isNearCorner(scaledX, scaledY, rect[2], rect[3], resizeThreshold)) {
				dragging = false;
				resizing = true;
				selectedCorner = 'bottomRight';
				console.log("Near bottomRight");
			} else if (inside1 || inside2) {
		//(Math.abs(scaledX - rect[0]) > 0 && Math.abs(scaledX - rect[2]) < 0 && Math.abs(scaledY - rect[3]) > 0 && Math.abs(scaledY - rect[1]) < 0) 
				cursor("grab");
				console.log("Near inside for dragging");
				// Otherwise check if inside the rectangle for dragging 
				// Traslazione
				dragging = true;
				offsetX = scaledX - rect[0]; 
				offsetY = scaledY - rect[1];
				console.log("offset: "+offsetX+" - "+offsetY);
			}else{
				cursor(ARROW);
			}
		}
		
		sketch.mouseDragged = function() {
			let scaledX = 0;
			let scaledY = 0;
			let r = boardData.radarData.regions;
			let selectedRectangle = r.selected -1;
			let rect = [];

			scaledX = mouseX - width /2;
			scaledY = height - mouseY;
			
			if(boardData.radarData.rot){
				// calcola il passaggio del rettangolo dal riferimento ruotato al non ruotato
				rect[0] = -r.xnr0[selectedRectangle];
				rect[1] = height - r.ynr0[selectedRectangle];
				rect[2] = -r.xnr1[selectedRectangle];
				rect[3] = height - r.ynr1[selectedRectangle];
				console.log("rect rot----------------------------");
			}else{		
				rect[0] = r.xnr0[selectedRectangle];
				rect[1] = r.ynr0[selectedRectangle];
				rect[2] = r.xnr1[selectedRectangle];
				rect[3] = r.ynr1[selectedRectangle];
				console.log("rect no rot----------------------------");
			}
				
		///---------CALCOLO NEL RIFERIMENTO NON RUOTATO--------------------------		
			if (dragging) {
					// Move the entire rectangle
					let widthd = rect[2] - rect[0];
					let heightd = rect[3] - rect[1];
					
					rect[0] = scaledX - offsetX;
					rect[1] = scaledY - offsetY;
					rect[2] = rect[0] + widthd;
					rect[3] = rect[1] + heightd;
			} else if (resizing) {	
				// Resize the rectangle based on selected corner
				if (selectedCorner === 'topLeft') {
					console.log("drag topLeft");
					rect[0] = scaledX;
					rect[1] = scaledY;
				} else if (selectedCorner === 'topRight') {
					console.log("drag topRight");
					rect[2] = scaledX;
					rect[1] = scaledY;
				} else if (selectedCorner === 'bottomLeft') {
					console.log("drag bottomLeft");
					rect[0] = scaledX;
					rect[3] = scaledY;
				} else if (selectedCorner === 'bottomRight') {
					rect[2] = scaledX;
					rect[3] = scaledY;
				}
				console.log("resize: "+scaledX+" - "+scaledY);
			}	
			// passaggio del risultato nel riferimento non ruotato o ruotato
			if(boardData.radarData.rot){
				r.xnr0[selectedRectangle] = -rect[0];
				r.ynr0[selectedRectangle] = height - rect[1];
				r.xnr1[selectedRectangle] = -rect[2];
				r.ynr1[selectedRectangle] = height - rect[3];
			}else{
				r.xnr0[selectedRectangle] = rect[0];
				r.ynr0[selectedRectangle] = rect[1];
				r.xnr1[selectedRectangle] = rect[2];
				r.ynr1[selectedRectangle] = rect[3];
			}
			// calcola i vertici significativi del rettangolo in metri
			r.x0[selectedRectangle] = mapInverse(r.xnr0[selectedRectangle], -width * 0.3, width * 0.3, -6, 6);
			r.y0[selectedRectangle] = mapInverse(r.ynr0[selectedRectangle], 0, -height, 0, -6);
			r.x1[selectedRectangle] = mapInverse(r.xnr1[selectedRectangle], -width * 0.3, width * 0.3, -6, 6);
			r.y1[selectedRectangle] = mapInverse(r.ynr1[selectedRectangle], 0, -height, 0, -6);
			updateInputsFromBoardDataRegion();
		}	

		sketch.mouseReleased = function () {
			dragging = false;
			resizing = false;
			selectedCorner = null;
			sketch.cursor(sketch.ARROW);
		}
	}, `radar-${boardID}`);	
}

function convertDateTimeToHumanReadable(dateTimeString) {
    const adjustedDateTime = adjustDateTime(dateTimeString);
    
    // Creazione di un oggetto Data da una stringa
    const dateTime = new Date(adjustedDateTime);

    // Ottenere componenti data e ora
    const year = dateTime.getFullYear();
    const month = padZero(dateTime.getMonth() + 1); // I mesi partono da 0 (gennaio)
    const day = padZero(dateTime.getDate());
    const hours = padZero(dateTime.getHours());
    const minutes = padZero(dateTime.getMinutes());
    const seconds = padZero(dateTime.getSeconds());

    // Creazione di una stringa comprensibile per l'utente
    const readableDateTime = `${day}/${month}/${year} ${hours}:${minutes}:${seconds}`;

    return readableDateTime;
}

// Funzione per aggiungere lo zero davanti alle cifre singole
function padZero(num) {
    return num.toString().padStart(2, '0');
}

function adjustDateTime(dateTimeString) {
    // Creazione di un oggetto Date dalla stringa fornita
    const dateTime = new Date(dateTimeString);

    // Fuso orario per l'Italia
    const userTimeZone = 'Europe/Rome'; // 'Europe/Rome' è il fuso orario dell'Italia

    // Calcolo dell'offset in millisecondi rispetto a UTC
    const offset = dateTime.getTimezoneOffset() * 60 * 1000;

    // Creazione di un nuovo oggetto Date con l'offset aggiunto per ottenere la data/ora corretta per il fuso orario specificato
    const adjustedDate = new Date(dateTime.getTime() - offset);

    return adjustedDate;
}

function updateInputsFromBoardDataRegion(boardID) {
	let r = boardData[boardID].radarData.regions;
	let selectedRectangle = r.selected -1;
	dataentry[0].value = roundTo(r.x0[selectedRectangle], 1);
	dataentry[1].value = roundTo(r.y0[selectedRectangle], 1);
	dataentry[2].value = roundTo(r.x1[selectedRectangle], 1);
	dataentry[3].value = roundTo(r.y1[selectedRectangle], 1);
	dataentry[4].value = roundTo(r.enabled[selectedRectangle], 1);
	dataentry[5].value = roundTo(r.type[selectedRectangle], 1);
}

function mapInverse(value, start2, stop2, start1, stop1) {
  return (value - start2) * (stop1 - start1) / (stop2 - start2) + start1;
}

function map(value, start1, stop1, start2, stop2) {
  return (value - start1) * (stop2 - start2) / (stop1 - start1) + start2;
}

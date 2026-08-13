document.addEventListener("DOMContentLoaded", () => {
    const airspace = document.getElementById("airspace");
    const demodBox = document.getElementById("demodBox");
    const classificationBox = document.getElementById("classificationResult");
    const actionBox = document.getElementById("actionResult");
    const osrDistSpan = document.getElementById("osrDist");
    const canvas = document.getElementById("signalCanvas");
    const ctx = canvas.getContext("2d");

    const blips = {}; // Store DOM elements for drones
    const droneState = {}; // Persistent classification state per drone

    // Connect WebSocket
    const ws = new WebSocket("ws://127.0.0.1:8000/ws/frontend");

    ws.onopen = () => {
        demodBox.textContent = "CONNECTED TO C2 SERVER. SCANNING...";
        demodBox.style.color = "#00ff41";
    };

    ws.onerror = () => {
        demodBox.textContent = "CONNECTION ERROR - IS THE C2 SERVER RUNNING?";
        demodBox.style.color = "#ff003c";
    };

    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === "RADAR_UPDATE") {
            updateRadar(msg.data);
        }
    };

    function updateRadar(drones) {
        drones.forEach(d => {
            // Coordinate mapping (1000x1000 simulated area mapped to radar box)
            const radarBox = airspace.parentElement;
            const pxX = (d.x / 1000) * radarBox.clientWidth;
            const pxY = (d.y / 1000) * radarBox.clientHeight;

            // Create blip element if it doesn't exist
            if (!blips[d.id]) {
                const el = document.createElement("div");
                el.className = "blip unclassified";
                
                const label = document.createElement("div");
                label.className = "blip-label";
                label.textContent = `ID-${d.id}`;
                el.appendChild(label);
                
                airspace.appendChild(el);
                blips[d.id] = el;
                droneState[d.id] = { classification: null, lastSeen: null };
            }

            const el = blips[d.id];
            el.style.left = `${pxX}px`;
            el.style.top = `${pxY}px`;

            // If an RF burst was intercepted this tick, update classification
            if (d.classification) {
                // Store persistent state
                droneState[d.id].classification = d.classification;
                droneState[d.id].action = d.action;
                droneState[d.id].payload = d.payload;
                droneState[d.id].osr_dist = d.osr_dist;
                droneState[d.id].iq_snippet = d.iq_snippet;
                droneState[d.id].lastSeen = Date.now();

                // Update the analysis panel with this drone's data
                updateAnalysisPanel(d);
            }

            // Apply persistent visual classification to the blip
            const state = droneState[d.id];
            if (state && state.classification) {
                const label = blips[d.id].querySelector(".blip-label");
                if (state.classification.includes("ROGUE") || state.classification.includes("UNKNOWN")) {
                    el.className = "blip rogue";
                    label.textContent = `ID-${d.id} [ROGUE]`;
                    label.style.color = "#ff003c";
                } else if (state.classification.includes("AUTHORIZED")) {
                    el.className = "blip friendly";
                    label.textContent = `ID-${d.id} [AUTH]`;
                    label.style.color = "#00ff41";
                } else if (state.classification === "ERROR" || state.classification === "UNINITIALIZED") {
                    el.className = "blip unclassified";
                    label.textContent = `ID-${d.id} [??]`;
                }
            }
        });
    }

    function updateAnalysisPanel(d) {
        // Update Demodulated Payload
        if (d.payload) {
            demodBox.textContent = d.payload;
            if(d.payload.includes("GARBLED")) {
                demodBox.style.color = "#ff003c";
            } else {
                demodBox.style.color = "#00f0ff";
            }
        }
        
        // Update Classification
        classificationBox.textContent = d.classification;
        if (d.classification.includes("ROGUE") || d.classification.includes("UNKNOWN")) {
            classificationBox.className = "classification-box rogue";
        } else if (d.classification.includes("AUTHORIZED")) {
            classificationBox.className = "classification-box friendly";
        } else {
            classificationBox.className = "classification-box waiting";
        }
            
        // Update OSR Latent Distance
        if (d.osr_dist !== undefined) {
            osrDistSpan.textContent = d.osr_dist;
            if(d.classification.includes("ROGUE") || d.classification.includes("UNKNOWN")) {
                osrDistSpan.style.color = "#ff003c";
            } else {
                osrDistSpan.style.color = "#00ff41";
            }
        }
        
        // Update Action
        if (d.action) {
            actionBox.textContent = d.action;
            actionBox.style.color = d.action.includes("IGNORED") ? "#ff003c" : "#00ff41";
        }

        // Draw I/Q Snippet
        if (d.iq_snippet) {
            drawSnippet(d.iq_snippet);
        }
    }

    function drawSnippet(iqReal) {
        ctx.fillStyle = "#000";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.strokeStyle = "#00f0ff";
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        
        const step = canvas.width / iqReal.length;
        for (let i = 0; i < iqReal.length; i++) {
            const x = i * step;
            // Map roughly -1.5 to 1.5 into canvas height
            const y = canvas.height/2 - (iqReal[i] * 20);
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.stroke();
    }
});

document.addEventListener("DOMContentLoaded", () => {
    const airspace = document.getElementById("airspace");
    const demodBox = document.getElementById("demodBox");
    const classificationBox = document.getElementById("classificationResult");
    const actionBox = document.getElementById("actionResult");
    const osrDistSpan = document.getElementById("osrDist");
    const canvas = document.getElementById("signalCanvas");
    const ctx = canvas.getContext("2d");

    const blips = {}; // Store DOM elements for drones

    // Connect WebSocket
    const ws = new WebSocket("ws://127.0.0.1:8000/ws/frontend");

    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === "RADAR_UPDATE") {
            updateRadar(msg.data);
        }
    };

    function updateRadar(drones) {
        drones.forEach(d => {
            // Coordinate mapping (1000x1000 simulated area mapped to 600x600 px)
            const pxX = (d.x / 1000) * 600;
            const pxY = (d.y / 1000) * 600;

            if (!blips[d.id]) {
                const el = document.createElement("div");
                el.className = "blip unclassified";
                
                const label = document.createElement("div");
                label.className = "blip-label";
                label.textContent = `ID-${d.id}`;
                el.appendChild(label);
                
                airspace.appendChild(el);
                blips[d.id] = el;
            }

            const el = blips[d.id];
            el.style.left = `${pxX}px`;
            el.style.top = `${pxY}px`;

            // If an RF burst was intercepted this tick, update panel
            if (d.classification) {
                if (d.classification.includes("ROGUE")) {
                    el.className = "blip rogue";
                } else {
                    el.className = "blip friendly";
                }

                updateAnalysisPanel(d);
            }
        });
    }

    function updateAnalysisPanel(d) {
        // Update Demodulated Payload
        demodBox.textContent = d.payload;
        if(d.payload.includes("GARBLED")) {
            demodBox.style.color = "#ff003c";
        } else {
            demodBox.style.color = "#00f0ff";
        }
        
        // Update Classification
        classificationBox.textContent = d.classification;
        classificationBox.className = d.classification.includes("ROGUE") 
            ? "classification-box rogue" : "classification-box friendly";
            
        // Update OSR Latent Distance
        osrDistSpan.textContent = d.osr_dist;
        if(d.classification.includes("ROGUE")) {
            osrDistSpan.style.color = "#ff003c";
        } else {
            osrDistSpan.style.color = "#00ff41";
        }
        
        // Update Action
        actionBox.textContent = d.action;
        actionBox.style.color = d.action.includes("IGNORED") ? "#ff003c" : "#00ff41";

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

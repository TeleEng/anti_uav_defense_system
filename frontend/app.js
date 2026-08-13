document.addEventListener("DOMContentLoaded", () => {
    const btnFriendly = document.getElementById("btnFriendly");
    const btnRogue = document.getElementById("btnRogue");
    const targetBlip = document.getElementById("targetBlip");
    
    const classificationBox = document.getElementById("classificationResult");
    const actionBox = document.getElementById("actionResult");
    
    const canvas = document.getElementById("signalCanvas");
    const ctx = canvas.getContext("2d");

    const API_URL = "http://127.0.0.1:8000/api/radar/scan";

    // Draw dummy static signal
    function drawFlatline() {
        ctx.fillStyle = "#000";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.strokeStyle = "#00f0ff";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(0, canvas.height / 2);
        ctx.lineTo(canvas.width, canvas.height / 2);
        ctx.stroke();
    }
    
    // Animate a chaotic RF burst
    function drawBurst(isRogue) {
        ctx.fillStyle = "#000";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        ctx.strokeStyle = isRogue ? "#ff003c" : "#00ff41";
        ctx.lineWidth = 2;
        ctx.beginPath();
        
        for (let x = 0; x < canvas.width; x += 2) {
            // Unknwon rogue drone has much higher hardware phase noise
            const noiseLevel = isRogue ? 60 : 15; 
            const yOffset = (Math.random() - 0.5) * noiseLevel + Math.sin(x/10)*20;
            const y = (canvas.height / 2) + yOffset;
            if (x === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.stroke();
    }

    drawFlatline();

    async function triggerRadar(type) {
        // Reset UI
        targetBlip.className = "target hidden";
        classificationBox.className = "classification-box waiting";
        classificationBox.textContent = "ANALYZING I/Q DATA...";
        actionBox.textContent = "--";
        
        drawBurst(type === 'unknown');

        try {
            const response = await fetch(API_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ drone_type: type })
            });

            const data = await response.json();
            
            // Randomize blip position slightly
            targetBlip.style.top = `${20 + Math.random() * 60}%`;
            targetBlip.style.left = `${20 + Math.random() * 60}%`;
            
            classificationBox.textContent = data.classification;
            actionBox.textContent = data.action_taken;

            if (data.classification === "KNOWN_FRIENDLY") {
                classificationBox.className = "classification-box friendly";
                targetBlip.className = "target friendly";
                actionBox.style.borderLeftColor = "#00ff41";
            } else {
                classificationBox.className = "classification-box rogue";
                targetBlip.className = "target"; // default is red
                actionBox.style.borderLeftColor = "#ff003c";
            }
            
        } catch (error) {
            console.error("API Error:", error);
            classificationBox.textContent = "API CONNECTION FAILED";
            actionBox.textContent = "Ensure c2_server.py is running on port 8000";
        }
    }

    btnFriendly.addEventListener("click", () => triggerRadar("friendly"));
    btnRogue.addEventListener("click", () => triggerRadar("unknown"));
});

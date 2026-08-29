// https://codepen.io/Leoschmittk/pen/vYyPYKx
// document.onclick = () => applyCursorRippleEffect(event);
// import { getMousePositionInScene } from '../marvel/scene.js';

document.querySelector('#scene').addEventListener("click", (event) => {
    applyCursorRippleEffect(event);
    event.preventDefault(); // Prevent default link behavior
    // this.reconnectNow();
});

// function getRandomColor(x) {
//     [r, b, g] = x
//     // Generate random variations
//     const variation = 100; // Adjust this value to control the range of color variation
//     const randomR = Math.min(255, Math.max(0, r + Math.floor(Math.random() * variation) - variation / 2));
//     const randomG = Math.min(255, Math.max(0, g + Math.floor(Math.random() * variation) - variation / 2));
//     const randomB = Math.min(255, Math.max(0, b + Math.floor(Math.random() * variation) - variation / 2));
//     // console.log(r, b, g);
//     // Convert back to hex
//     return [randomR, randomG, randomB];
// }

// let last_color = [0xFF, 0xFF, 0xFF]

function applyCursorRippleEffect(e) {
    const ripple = document.createElement("div");

    ripple.className = "ripple";
    document.body.appendChild(ripple);

    let pos = {x: e.clientX, y: e.clientY}
    // console.log(pos)
    // let pos = getMousePositionInScene(e.clientX, e.clientY);

    // const randomColor = getRandomColor(last_color);
    // ripple.style.borderColor = `rgba(${randomColor[0]}, ${randomColor[1]}, ${randomColor[2]}, .59)`;
    // last_color = randomColor
    // console.log(last_color);

    ripple.style.left = `${pos.x}px`;
    ripple.style.top = `${pos.y}px`;
    ripple.style.animation = `ripple-effect .4s  linear`;
    ripple.onanimationend = () => {
        document.body.removeChild(ripple);
    };
}

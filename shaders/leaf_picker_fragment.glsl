#version 330 core
in vec2 UV;
out vec4 FragColor;

uniform sampler2D tex;
uniform bool isTexture;
uniform vec4 drawColor;

void main() {
    if (isTexture) {
        vec4 col = texture(tex, UV);
        if (col.a < 0.05) discard;
        FragColor = col;
    } else {
        FragColor = drawColor;
    }
}
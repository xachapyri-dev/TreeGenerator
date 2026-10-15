#version 330 core
layout (location = 0) in vec2 inPos;
layout (location = 1) in vec2 inUV;

uniform mat4 ortho;

out vec2 UV;

void main() {
    UV = inUV;
    gl_Position = ortho * vec4(inPos, 0.0, 1.0);
}
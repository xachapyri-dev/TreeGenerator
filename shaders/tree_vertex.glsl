#version 330 core
layout (location = 0) in vec3 inPos;
layout (location = 1) in vec3 inNorm;
layout (location = 2) in vec2 inUV;
layout (location = 3) in vec3 inTangent;

uniform mat4 model;
uniform mat4 view;
uniform mat4 proj;

out vec3 FragPos;
out vec2 TexCoords;
out mat3 TBN;

void main() {
    FragPos = vec3(model * vec4(inPos, 1.0));
    TexCoords = inUV;

    vec3 T = normalize(vec3(model * vec4(inTangent, 0.0)));
    vec3 N = normalize(vec3(model * vec4(inNorm, 0.0)));
    vec3 B = cross(N, T);
    TBN = mat3(T, B, N);

    gl_Position = proj * view * vec4(FragPos, 1.0);
}
#version 330 core
out vec4 FragColor;

in vec3 FragPos;
in vec2 TexCoords;
in mat3 TBN;

uniform sampler2D texAlbedo;
uniform sampler2D texNormal;
uniform sampler2D texRoughness;
uniform sampler2D texTransmission;
uniform sampler2D texAO;

uniform bool hasAlbedo;
uniform bool hasNormal;
uniform bool hasRoughness;
uniform bool hasTransmission;
uniform bool hasAO;

uniform vec3 lightPos;
uniform vec3 viewPos;

void main() {
    vec4 albedo = hasAlbedo ? texture(texAlbedo, TexCoords) : vec4(0.55, 0.55, 0.55, 1.0);
    if (albedo.a < 0.25) discard;
    vec3 norm = normalize(TBN[2]);
    if (hasNormal) {
        vec3 normalMap = texture(texNormal, TexCoords).rgb * 2.0 - 1.0;
        norm = normalize(TBN * normalMap);
    }
    float roughness = hasRoughness ? texture(texRoughness, TexCoords).r : 0.75;
    float ao = hasAO ? texture(texAO, TexCoords).r : 1.0;
    float transmission = hasTransmission ? texture(texTransmission, TexCoords).r : 0.0;
    vec3 lightColor = vec3(1.0, 0.98, 0.94);
    vec3 ambient = vec3(0.28) * albedo.rgb * ao;
    vec3 lightDir = normalize(lightPos - FragPos);
    vec3 viewDir = normalize(viewPos - FragPos);
    float diff = max(dot(norm, lightDir), 0.0);
    vec3 diffuse = diff * albedo.rgb * lightColor;
    float transLight = max(dot(-norm, lightDir), 0.0);
    vec3 translucency = transLight * transmission * albedo.rgb * lightColor * 1.5;
    vec3 halfwayDir = normalize(lightDir + viewDir);
    float spec = pow(max(dot(norm, halfwayDir), 0.0), (1.0 - roughness) * 64.0 + 2.0);
    vec3 specular = vec3(0.2) * spec * lightColor;
    vec3 finalColor = ambient + diffuse + translucency + specular;
    FragColor = vec4(finalColor, albedo.a);
}
package br.com.erudio.config;

import com.fasterxml.jackson.annotation.JsonInclude;
import org.springframework.boot.http.converter.autoconfigure.ServerHttpMessageConvertersCustomizer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.converter.yaml.JacksonYamlHttpMessageConverter;
import tools.jackson.dataformat.yaml.YAMLMapper;

@Configuration
public class JacksonConfig {

    @Bean
    ServerHttpMessageConvertersCustomizer yamlMessageConverterCustomizer() {
        return builder -> builder.withYamlConverter(new JacksonYamlHttpMessageConverter(
            YAMLMapper.builder().changeDefaultPropertyInclusion(
                incl -> incl.withValueInclusion(JsonInclude.Include.NON_NULL))));
    }
}

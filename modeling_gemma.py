import torch
from torch import nn
from typing import Optional, Tuple
from modeling_siglip import SiglipVisionConfig, SiglipVisionModel


class KVCache:
    pass



# the llm model
class GemmaConfig():
    def __init__(
        self,
        vocab_size,
        hidden_size,
        intermediate_size,
        num_hidden_layers,
        num_attention_heads,
        num_key_value_heads,
        head_dim=256,
        max_position_embeddings=8192,
        rms_norm_eps=1e-6,
        rope_theta=10000.0,
        attention_bias=False,
        attention_dropout=0.0,
        pad_token_id=None,
        **kwargs,
    ):
        super().__init__()
        self.vocab_size = vocab_size
        self.max_postion_embeddings = max_position_embeddings
        self.hidden_size = hidden_size
        self.intermediate_size = intermediate_size
        self.num_hidden_layers = num_hidden_layers
        self.num_attention_heads = num_attention_heads
        self.head_dim = head_dim
        self.num_key_value_heads = num_key_value_heads
        self.rms_norm_eps = rms_norm_eps
        self.rope_theta = rope_theta
        self.attention_bias = attention_bias
        self.attention_dropout = attention_dropout
        self.pad_token_id = pad_token_id
        
        
class PaliGemmaConfig():
    def __init__(
        self,
        vision_config=None,
        text_config=None,
        ignore_index=-100,
        image_token_index=256000,
        vocab_size=257152,
        projection_dim=2048,
        hidden_size=2048,
        pad_token_id=None,
        **kwargs,
        ):
        super.__init__()
        self.ignore_index = ignore_index
        self.image_token_index = image_token_index
        self.vocab_size = vocab_size
        self.projection_dim = projection_dim
        self.hidden_size = hidden_size
        self.vision_config = vision_config
        self.is_encoder_decoder = False
        self.pad_token_id = pad_token_id
        
        self.vision_config = SiglipVisionConfig(**vision_config)
        self.text_config = text_config
        
        self.text_config = GemmaConfig(**text_config, pad_token_id=pad_token_id)
        self.vocab_size = self.text_config.vocab_size

        self.text_config.num_image_tokens = (self.vision_config.image_size // self.vision_config.patch_size) ** 2
        self.vision_config.projection_dim = projection_dim
        
        
class PaliGemmaMultiModalProjector(nn.Module):
    pass

class GemmaForCausalLM():
    pass    


class PaliGemmaForConditionalGeneration(nn.Module):
    def __init__(self, config: PaliGemmaConfig):
        super().__init__()
        self.config = config
        self.vision_tower = SiglipVisionModel(config.vision_config)
        self.multi_modal_projector = PaliGemmaMultiModalProjector(config)
        self.vocab_sie = config.vocab_size
        
        language_model = GemmaForCausalLM(config.text_config)
        self.language_mmodel = language_model
        
        if self.config.pad_token_id:
            self.pad_token_id = self.config.pad_token_id
        else:
            self.pad_token_id = -1
            
    def tie_weights(self):
        return self.language_mmodel.tie_weights()


    def forward(
        self,
        inputs_ids: torch.LongTensor=None,
        pixel_values: torch.FloatTensor=None,
        attention_mask: Optional[torch.tensor]=None,
        kv_cache: Optional[KVCache]=None,
    ) -> Tuple:
        assert torch.all(attention_mask==1), "We do not pad the input"
        
        # 1. extract the input embeddings.
        # shape: (batch_size, seq_len, hidden_size)
        inputs_embeds = self.language_mmodel.get_input_embeddings()(inputs_ids)
        
        # 2. Merge text and images.
        # shape: (batch_size),channels, height, width) -> (batch_size, num_patches, embed_dim)
        selected_image_feature = self.vision_tower(pixel_values.to(inputs_embeds.dtype))
        
        # 3. resize the image feature into size compatible with the LLM
        image_features = self.multi_modal_projector(selected_image_feature)
        
        # 4. merge the token from vision model to the text token (fill up place-holder)
        inputs_embeds, attention_mask, position_ids = self._merge_input_ids_with_image_features(
            image_features, # from vit.
            inputs_embeds, # from llm
            inputs_ids, # from tokenizer.
            attention_mask, # from tokenizer.
            kv_cache # cache for optimality.
            )
        
        outputs = self.language_mmodel(
            attention_mask=attention_mask,
            position_ids=position_ids,
            inputs_embeds=inputs_embeds,
            kv_cache=kv_cache
        )
        
        return outputs

        
        
        

config = SiglipVisionConfig()
model = SiglipVisionModel(config=config)
print (model)

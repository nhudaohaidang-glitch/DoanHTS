// Insert inside the recipient's own top/bus wrapper. Signals are placeholders.
ai_core u_ai (
 .clk(clk), .rst_n(ai_reset_n), .start(ai_start_one_cycle), .feat(ai_features_q),
 .busy(ai_busy), .done(ai_done), .class_id(ai_class), .scores(ai_scores_packed)
);

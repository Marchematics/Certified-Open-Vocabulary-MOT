#!/usr/bin/env Rscript

# Dense materials figure rebuild.
#
# Contract:
# - Backend: R only.
# - Six large panels, each internally composed of real quantitative
#   mini-visualizations (faceted bars, point intervals, line traces or heatmaps).
# - No panel is a text-card/status-tile substitute for data.

required_packages <- c("ggplot2", "patchwork", "svglite")
missing_packages <- required_packages[!vapply(required_packages, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing_packages) > 0) {
  stop(
    paste0(
      "Missing required R packages: ",
      paste(missing_packages, collapse = ", "),
      ". Install with install.packages(c(",
      paste(sprintf('\"%s\"', missing_packages), collapse = ", "),
      "))."
    ),
    call. = FALSE
  )
}

library(ggplot2)
library(patchwork)

args <- commandArgs(FALSE)
script_file <- sub("^--file=", "", args[grep("^--file=", args)[1]])
if (is.na(script_file) || !nzchar(script_file)) {
  script_file <- "scripts/build_figure3_materials_density.R"
}
root <- normalizePath(file.path(dirname(script_file), ".."), mustWork = TRUE)
data_dir <- file.path(root, "data")
out_dir <- file.path(root, "figures", "figure3_assets", "rebuild")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

pal <- c(
  ink = "#272727",
  grid = "#E6E6E6",
  raw = "#9A9A9A",
  topR = "#C8DCE8",
  parc = "#5EA6C8",
  prevented = "#76B7B2",
  refusal = "#D96B5F",
  boundary = "#D6A55D",
  support = "#C8DCE8",
  threshold = "#7C6BAA",
  post_e = "#5F8FB5",
  oracle = "#B9D8C2"
)

theme_mat <- function(base_size = 5.6, base_family = "Arial") {
  theme_classic(base_size = base_size, base_family = base_family) +
    theme(
      axis.line = element_line(linewidth = 0.25, colour = pal[["ink"]]),
      axis.ticks = element_line(linewidth = 0.25, colour = pal[["ink"]]),
      axis.text = element_text(size = base_size - 0.8, colour = pal[["ink"]]),
      axis.title = element_text(size = base_size),
      axis.title.x = element_text(margin = margin(t = 2.5, unit = "pt")),
      legend.title = element_text(size = base_size - 0.5),
      legend.text = element_text(size = base_size - 0.9),
      legend.key.size = unit(0.18, "cm"),
      strip.background = element_rect(fill = "#F2F4F5", colour = NA),
      strip.text = element_text(size = base_size - 0.6, face = "bold"),
      plot.title = element_text(size = base_size + 0.55, face = "bold", hjust = 0),
      plot.margin = margin(2.5, 3.5, 8.0, 3.5, "pt"),
      panel.grid.major.y = element_line(linewidth = 0.18, colour = pal[["grid"]]),
      panel.grid.major.x = element_blank(),
      panel.grid.minor = element_blank()
    )
}
theme_set(theme_mat())

save_panel <- function(plot, stem, width_mm = 91, height_mm = 48, dpi = 600) {
  base <- file.path(out_dir, stem)
  w <- width_mm / 25.4
  h <- height_mm / 25.4
  svglite::svglite(paste0(base, ".svg"), width = w, height = h)
  print(plot)
  invisible(dev.off())
  grDevices::cairo_pdf(paste0(base, ".pdf"), width = w, height = h, family = "Arial")
  print(plot)
  invisible(dev.off())
  grDevices::png(paste0(base, ".png"), width = w, height = h, units = "in", res = dpi, type = "cairo")
  print(plot)
  invisible(dev.off())
  message("wrote ", file.path("figures", "figure3_assets", "rebuild", paste0(stem, ".pdf")))
}

read_table <- function(name) read.csv(file.path(data_dir, name), stringsAsFactors = FALSE)

primary <- subset(read_table("table_fixed_budget_primary.csv"), rho == 0.10 & alpha == 0.10)
seed_rows <- subset(read_table("table_fixed_budget_seed_rows.csv"), rho == 0.10 & alpha == 0.10)
raw_panel <- read_table("materials_raw_vs_parc_ftr_panel.csv")
robust <- subset(read_table("materials_threshold_robustness_figure.csv"), rho == 0.10 & alpha == 0.10)
gamma <- subset(read_table("materials_gamma_sensitivity_heatmap.csv"), rho == 0.10 & alpha == 0.10)
block <- subset(read_table("table_materials_block_sensitivity.csv"), rho == 0.10 & alpha == 0.10)
random_control <- subset(read_table("table_materials_random_score_control.csv"), rho == 0.10 & alpha == 0.10)
high_volume <- subset(read_table("table_materials_high_volume_refusal.csv"), rho == 0.10 & alpha == 0.10)

short_model <- function(x) {
  out <- x
  out[out == "CGCNN 10-member ensemble"] <- "CGCNN"
  out[out == "ALIGNN-FF"] <- "ALIGNN"
  out
}
primary$model <- factor(short_model(primary$model_family), levels = c("CGCNN", "ALIGNN", "MEGNet"))
seed_rows$model <- factor(short_model(seed_rows$model_family), levels = c("CGCNN", "ALIGNN", "MEGNet"))
primary$K_label <- factor(paste0("K=", primary$K), levels = paste0("K=", c(100, 300, 500, 1000, 5000)))
seed_rows$K_label <- factor(paste0("K=", seed_rows$K), levels = paste0("K=", c(100, 300, 500, 1000, 5000)))

# Panel a: model x K mini bar charts for raw, matched-prefix and certified FTR.
ftr_long <- rbind(
  data.frame(primary[, c("model", "K_label")], method = "raw K", value = primary$raw_topK_FTR_mean),
  data.frame(primary[, c("model", "K_label")], method = "raw R", value = primary$raw_topR_FTR_mean),
  data.frame(primary[, c("model", "K_label")], method = "PARC", value = primary$PARC_FTR_mean)
)
ftr_long$method <- factor(ftr_long$method, levels = c("raw K", "raw R", "PARC"))
p_a <- ggplot(ftr_long, aes(x = method, y = value, fill = method)) +
  geom_hline(yintercept = 0.10, linewidth = 0.20, linetype = "dashed", colour = pal[["ink"]]) +
  geom_col(width = 0.65, colour = "white", linewidth = 0.12) +
  facet_grid(model ~ K_label) +
  scale_fill_manual(values = c(`raw K` = pal[["raw"]], `raw R` = pal[["topR"]], PARC = pal[["parc"]])) +
  scale_y_continuous(limits = c(0, 0.62), breaks = c(0, 0.3, 0.6)) +
  labs(x = NULL, y = "FTR", fill = NULL, title = "Model-budget FTR frontier") +
  theme(
    axis.text.x = element_text(angle = 30, hjust = 1),
    legend.position = "bottom",
    legend.margin = margin(1, 0, 2, 0, "pt"),
    legend.box.margin = margin(0, 0, 2, 0, "pt")
  )
save_panel(p_a, "figure_3a_model_budget_ftr_grid", 91, 52)

# Panel b: model x K mini bar charts for downstream follow-up counts.
count_long <- rbind(
  data.frame(primary[, c("model", "K_label")], metric = "raw unstable", value = primary$raw_unstable_count_mean),
  data.frame(primary[, c("model", "K_label")], metric = "PARC unstable", value = primary$PARC_unstable_count_mean),
  data.frame(primary[, c("model", "K_label")], metric = "prevented", value = primary$prevented_unstable_followups_mean)
)
count_long$metric <- factor(count_long$metric, levels = c("raw unstable", "PARC unstable", "prevented"))
p_b <- ggplot(count_long, aes(x = metric, y = value, fill = metric)) +
  geom_col(width = 0.65, colour = "white", linewidth = 0.12) +
  facet_grid(model ~ K_label, scales = "free_y") +
  scale_fill_manual(values = c(`raw unstable` = pal[["raw"]], `PARC unstable` = pal[["parc"]], prevented = pal[["prevented"]])) +
  scale_y_continuous(expand = expansion(mult = c(0, 0.14))) +
  labs(x = NULL, y = "count / seed", fill = NULL, title = "Follow-up objects changed") +
  theme(
    axis.text.x = element_text(angle = 30, hjust = 1),
    legend.position = "bottom",
    legend.margin = margin(1, 0, 2, 0, "pt"),
    legend.box.margin = margin(0, 0, 2, 0, "pt")
  )
save_panel(p_b, "figure_3b_followup_count_grid", 91, 52)

# Panel c: seed-level distributions for raw and PARC FTR.
seed_long <- rbind(
  data.frame(seed_rows[, c("model", "K_label", "seed")], method = "raw K", value = seed_rows$raw_topK_FTR),
  data.frame(seed_rows[, c("model", "K_label", "seed")], method = "PARC", value = seed_rows$PARC_FTR)
)
seed_long$method <- factor(seed_long$method, levels = c("raw K", "PARC"))
p_c <- ggplot(seed_long, aes(x = method, y = value, fill = method)) +
  geom_hline(yintercept = 0.10, linewidth = 0.20, linetype = "dashed", colour = pal[["ink"]]) +
  geom_boxplot(width = 0.58, outlier.size = 0.25, linewidth = 0.18) +
  facet_grid(model ~ K_label) +
  scale_fill_manual(values = c(`raw K` = pal[["raw"]], PARC = pal[["parc"]])) +
  scale_y_continuous(limits = c(0, 0.75), breaks = c(0, 0.3, 0.6)) +
  labs(x = NULL, y = "seed FTR", fill = NULL, title = "Seed-level FTR distributions") +
  theme(
    axis.text.x = element_text(angle = 30, hjust = 1),
    legend.position = "bottom",
    legend.margin = margin(1, 0, 2, 0, "pt"),
    legend.box.margin = margin(0, 0, 2, 0, "pt")
  )
save_panel(p_c, "figure_3c_seed_distribution_grid", 91, 52)

# Panel d: nearest practical alternatives for rows used in the baseline paragraph.
row_name <- paste0("K=", raw_panel$K, ", a=", raw_panel$alpha)
alt_ftr <- rbind(
  data.frame(row = row_name, metric = "FTR", method = "raw K", value = raw_panel$raw_topK_FTR),
  data.frame(row = row_name, metric = "FTR", method = "raw R", value = raw_panel$raw_topR_FTR),
  data.frame(row = row_name, metric = "FTR", method = "split", value = raw_panel$split_conformal_FTR),
  data.frame(row = row_name, metric = "FTR", method = "post-e", value = raw_panel$post_filter_e_threshold_FTR),
  data.frame(row = row_name, metric = "FTR", method = "e-BH", value = raw_panel$e_BH_full_pool_FTR),
  data.frame(row = row_name, metric = "FTR", method = "PARC", value = raw_panel$PARC_FTR),
  data.frame(row = row_name, metric = "release", method = "raw K", value = raw_panel$K),
  data.frame(row = row_name, metric = "release", method = "raw R", value = raw_panel$PARC_release_size),
  data.frame(row = row_name, metric = "release", method = "split", value = raw_panel$split_conformal_release_size),
  data.frame(row = row_name, metric = "release", method = "post-e", value = raw_panel$post_filter_e_threshold_release_size),
  data.frame(row = row_name, metric = "release", method = "e-BH", value = raw_panel$e_BH_full_pool_release_size),
  data.frame(row = row_name, metric = "release", method = "PARC", value = raw_panel$PARC_release_size)
)
alt_ftr <- alt_ftr[!is.na(alt_ftr$value), ]
alt_ftr$method <- factor(alt_ftr$method, levels = c("raw K", "raw R", "split", "post-e", "e-BH", "PARC"))
alt_ftr$row <- factor(alt_ftr$row, levels = row_name)
p_d <- ggplot(alt_ftr, aes(x = method, y = value, fill = method)) +
  geom_col(width = 0.62, colour = "white", linewidth = 0.12) +
  facet_grid(metric ~ row, scales = "free_y") +
  scale_fill_manual(values = c(`raw K` = pal[["raw"]], `raw R` = pal[["topR"]], split = pal[["threshold"]], `post-e` = pal[["post_e"]], `e-BH` = pal[["boundary"]], PARC = pal[["parc"]])) +
  labs(x = NULL, y = NULL, fill = NULL, title = "Nearest practical alternatives") +
  theme(
    axis.text.x = element_text(angle = 35, hjust = 1),
    legend.position = "bottom",
    legend.margin = margin(1, 0, 2, 0, "pt"),
    legend.box.margin = margin(0, 0, 2, 0, "pt")
  )
save_panel(p_d, "figure_3d_baseline_alternative_grid", 91, 52)

# Panel e: stability-definition robustness.
robust$variant_short <- robust$variant
robust$variant_short <- gsub("conservative_clear_stable_observed_", "stable+", robust$variant_short)
robust$variant_short <- gsub("margin_excluded_", "margin-", robust$variant_short)
robust$variant_short <- gsub("_", " ", robust$variant_short)
robust$K_label <- factor(paste0("K=", robust$K), levels = paste0("K=", sort(unique(robust$K))))
robust_long <- rbind(
  data.frame(variant = robust$variant_short, K_label = robust$K_label, metric = "FTR", value = robust$actual_FTR_mean),
  data.frame(variant = robust$variant_short, K_label = robust$K_label, metric = "release", value = robust$mean_release / robust$K),
  data.frame(variant = robust$variant_short, K_label = robust$K_label, metric = "mass", value = pmin(robust$best_mass_ratio_mean, 2) / 2)
)
robust_long$metric <- factor(robust_long$metric, levels = c("FTR", "release", "mass"))
p_e <- ggplot(robust_long, aes(x = K_label, y = value, colour = metric, shape = metric, group = metric)) +
  geom_hline(yintercept = 0.10, linewidth = 0.20, linetype = "dashed", colour = pal[["ink"]]) +
  geom_line(linewidth = 0.34) +
  geom_point(size = 0.90) +
  facet_wrap(~variant, ncol = 2) +
  scale_colour_manual(values = c(FTR = pal[["raw"]], release = pal[["parc"]], mass = pal[["boundary"]])) +
  labs(x = NULL, y = "scaled", colour = NULL, shape = NULL, title = "Stability-definition robustness") +
  theme(
    axis.text.x = element_text(angle = 35, hjust = 1),
    legend.position = "bottom",
    legend.justification = "left",
    legend.margin = margin(1, 0, 1, 0, "pt"),
    legend.box.margin = margin(1, 0, 1, 0, "pt"),
    plot.title = element_text(margin = margin(0, 0, 4, 0, "pt")),
    plot.margin = margin(3, 4, 6, 4, "pt")
  )
save_panel(p_e, "figure_3e_threshold_robustness_grid", 91, 54)

# Panel f: gamma/block/control stress diagnostics.
gamma$gamma_label <- factor(sprintf("%.2f", gamma$gamma), levels = sprintf("%.2f", sort(unique(gamma$gamma))))
gamma$K_label <- factor(paste0("K=", gamma$K), levels = paste0("K=", sort(unique(gamma$K))))
gamma_max <- max(gamma$actual_FTR_mean, na.rm = TRUE)
p_f1 <- ggplot(gamma, aes(x = gamma_label, y = K_label, fill = actual_FTR_mean)) +
  geom_tile(colour = NA, linewidth = 0) +
  scale_fill_gradient(
    low = "#E8F2F6",
    high = pal[["refusal"]],
    limits = c(0, gamma_max),
    breaks = c(0, gamma_max),
    labels = sprintf("%.2f", c(0, gamma_max)),
    guide = guide_colourbar(
      label.position = "bottom",
      direction = "horizontal",
      barwidth = unit(1.55, "cm"),
      barheight = unit(0.14, "cm"),
      ticks = TRUE
    )
  ) +
  scale_x_discrete(expand = c(0, 0)) +
  scale_y_discrete(expand = c(0, 0)) +
  labs(x = "gamma", y = NULL, fill = NULL, title = "Gamma sensitivity") +
  theme(
    axis.line = element_blank(),
    axis.ticks = element_blank(),
    panel.grid = element_blank(),
    legend.position = "top",
    legend.justification = "left",
    legend.margin = margin(0, 0, 1, 0, "pt"),
    legend.box.margin = margin(0, 0, 1, 0, "pt"),
    legend.title = element_blank(),
    legend.text = element_text(size = 4.4),
    axis.text.x = element_text(angle = 35, hjust = 1, size = 4.6)
  )

block$block_short <- block$block_definition
block$block_short[block$block_definition == "composition_family_pair"] <- "comp. family"
block$block_short[block$block_definition == "chemical_system"] <- "chem. system"
block$block_short[block$block_definition == "wyckoff_family"] <- "Wyckoff"
block$K_label <- factor(paste0("K=", block$K), levels = paste0("K=", sort(unique(block$K))))
block_long <- rbind(
  data.frame(block = block$block_short, K_label = block$K_label, metric = "FTR", value = block$actual_FTR_mean),
  data.frame(block = block$block_short, K_label = block$K_label, metric = "mass", value = pmin(block$best_mass_ratio_mean, 2) / 2)
)
p_f2 <- ggplot(block_long, aes(x = K_label, y = value, fill = metric)) +
  geom_col(position = position_dodge(width = 0.65), width = 0.58, colour = "white", linewidth = 0.12) +
  facet_wrap(~block, nrow = 1) +
  scale_fill_manual(values = c(FTR = pal[["raw"]], mass = pal[["support"]])) +
  labs(x = NULL, y = "scaled", fill = NULL, title = "Block sensitivity") +
  theme(
    axis.text.x = element_text(angle = 35, hjust = 1),
    legend.position = "top",
    legend.justification = "left",
    legend.margin = margin(0, 0, 1, 0, "pt"),
    legend.box.margin = margin(0, 0, 1, 0, "pt")
  )

control <- rbind(
  data.frame(K = random_control$K, source = "random score", metric = "raw FTR", value = random_control$raw_topK_actual_FTR_mean),
  data.frame(K = random_control$K, source = "random score", metric = "release", value = random_control$mean_release / random_control$K),
  data.frame(K = high_volume$K, source = "high volume", metric = "raw FTR", value = high_volume$raw_topK_actual_FTR_mean),
  data.frame(K = high_volume$K, source = "high volume", metric = "release", value = high_volume$mean_release / high_volume$K)
)
p_f3 <- ggplot(control, aes(x = factor(K), y = value, fill = metric)) +
  geom_col(position = position_dodge(width = 0.65), width = 0.58, colour = "white", linewidth = 0.12) +
  facet_wrap(~source, nrow = 1, scales = "free_x") +
  scale_fill_manual(values = c(`raw FTR` = pal[["raw"]], release = pal[["refusal"]])) +
  scale_y_continuous(limits = c(0, 1.05), breaks = c(0, 1)) +
  labs(x = "K", y = NULL, fill = NULL, title = "Refusal controls") +
  theme(
    legend.position = "top",
    legend.justification = "left",
    legend.margin = margin(0, 0, 1, 0, "pt"),
    legend.box.margin = margin(0, 0, 1, 0, "pt")
  )

p_f <- p_f1 | (p_f2 / p_f3 + plot_layout(heights = c(1, 1))) +
  plot_layout(widths = c(1.08, 0.92))
save_panel(p_f, "figure_3f_gamma_block_control_grid")

message("Done. Dense materials panel PDFs are ready for LaTeX assembly.")

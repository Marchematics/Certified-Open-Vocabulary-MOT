#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(ggplot2)
  library(patchwork)
  library(scales)
})

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script_path <- if (length(file_arg)) sub("^--file=", "", file_arg[[1]]) else "scripts/build_figure5_materials_robustness_density.R"
root <- normalizePath(file.path(dirname(script_path), ".."), mustWork = FALSE)
if (!dir.exists(file.path(root, "data"))) root <- getwd()
data_dir <- file.path(root, "data")
out_dir <- file.path(root, "figures", "figure5_assets", "rebuild")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

pal <- c(
  parc = "#5FA8C9",
  alignn = "#D9A441",
  cgcnn = "#4778A8",
  megnet = "#76B7B2",
  baseline = "#B9C2CD",
  alt = "#7C6FB0",
  random = "#E77C70",
  neutral = "#313845",
  pale = "#EAEFF3"
)

theme_set(
  theme_classic(base_size = 5.4, base_family = "Arial") +
    theme(
      axis.line = element_line(linewidth = 0.25, colour = "#222222"),
      axis.ticks = element_line(linewidth = 0.25, colour = "#222222"),
      axis.ticks.length = unit(1.3, "pt"),
      panel.grid.major.y = element_line(linewidth = 0.18, colour = "#E7E7E7"),
      panel.grid.major.x = element_blank(),
      strip.background = element_rect(fill = "#F1F3F5", colour = NA),
      strip.text = element_text(size = 5.3, face = "bold", margin = margin(0.6, 0, 0.8, 0)),
      legend.position = "bottom",
      legend.title = element_blank(),
      legend.text = element_text(size = 5.1),
      plot.title = element_text(size = 6.2, face = "bold"),
      plot.margin = margin(2, 2, 2, 2)
    )
)

read_table <- function(name) read.csv(file.path(data_dir, name), check.names = FALSE, stringsAsFactors = FALSE)

save_panel <- function(plot, stem, width_mm = 183, height_mm = 52) {
  w <- width_mm / 25.4
  h <- height_mm / 25.4
  pdf_path <- file.path(out_dir, paste0(stem, ".pdf"))
  svg_path <- file.path(out_dir, paste0(stem, ".svg"))
  png_path <- file.path(out_dir, paste0(stem, ".png"))
  grDevices::cairo_pdf(pdf_path, width = w, height = h, family = "Arial")
  print(plot)
  grDevices::dev.off()
  svglite::svglite(svg_path, width = w, height = h, system_fonts = list(sans = "Arial"))
  print(plot)
  grDevices::dev.off()
  if (requireNamespace("pdftools", quietly = TRUE) && requireNamespace("png", quietly = TRUE)) {
    img <- pdftools::pdf_render_page(pdf_path, page = 1, dpi = 320)
    png::writePNG(img, png_path)
  }
  cat("wrote", pdf_path, "\n")
}

source_label <- function(x) {
  ifelse(grepl("alignn", x), "ALIGNN-FF",
    ifelse(grepl("cgcnn", x), "CGCNN", ifelse(grepl("megnet", x), "MEGNet", x))
  )
}

variant_label <- function(x) {
  out <- gsub("_", " ", x)
  out <- gsub("exact stable primary", "exact stable", out)
  out <- gsub("tolerance positive 25meV", "+25 meV tolerance", out)
  out <- gsub("margin excluded 25meV", "25 meV margin excl.", out)
  out <- gsub("conservative clear stable observed 25meV", "clear-stable", out)
  out
}

long_rows <- function(df, id_cols, value_cols, labels = NULL) {
  parts <- lapply(value_cols, function(v) {
    z <- df[, c(id_cols, v), drop = FALSE]
    names(z)[ncol(z)] <- "value"
    z$metric <- if (!is.null(labels) && v %in% names(labels)) labels[[v]] else v
    z
  })
  do.call(rbind, parts)
}

panel_a_threshold_surface <- function() {
  thr <- read_table("materials_threshold_robustness_figure.csv")
  thr$source <- source_label(thr$proposal_source)
  thr$variant_label <- variant_label(thr$variant)
  thr$release_fraction <- ifelse(thr$K > 0, thr$mean_release / thr$K, 0)
  thr$seed_fraction <- thr$non_empty_seeds / thr$seeds
  thr$e_margin <- thr$max_observed_e_mean / thr$required_e
  thr$mass_log10 <- log10(pmax(thr$best_mass_ratio_mean, 1e-3))
  long <- long_rows(
    thr,
    c("source", "variant_label", "K"),
    c("actual_FTR_mean", "raw_topK_actual_FTR_mean", "release_fraction",
      "seed_fraction", "mass_log10", "released_boundary_rate_25meV_mean"),
    c(
      actual_FTR_mean = "PARC FTR",
      raw_topK_actual_FTR_mean = "raw top-K FTR",
      release_fraction = "released/requested",
      seed_fraction = "non-empty seeds",
      mass_log10 = "log10 mass ratio",
      released_boundary_rate_25meV_mean = "boundary-rate"
    )
  )
  long$metric <- factor(long$metric, levels = c(
    "PARC FTR", "raw top-K FTR", "released/requested",
    "non-empty seeds", "log10 mass ratio", "boundary-rate"
  ))
  ggplot(long, aes(factor(K), value, group = source, colour = source)) +
    geom_hline(data = data.frame(metric = c("PARC FTR", "raw top-K FTR"), y = 0.10),
               aes(yintercept = y), inherit.aes = FALSE, linetype = "dashed", linewidth = 0.24, colour = "#606060") +
    geom_line(linewidth = 0.35) +
    geom_point(size = 0.72) +
    facet_grid(metric ~ variant_label, scales = "free_y") +
    scale_colour_manual(values = c("ALIGNN-FF" = unname(pal["alignn"]), "CGCNN" = unname(pal["cgcnn"]))) +
    labs(x = "requested K", y = NULL, title = "Stability-definition robustness surfaces") +
    theme(axis.text.x = element_text(angle = 35, hjust = 1))
}

panel_b_matched_baseline_grid <- function() {
  raw <- read_table("materials_raw_vs_parc_ftr_panel.csv")
  raw$row <- paste0(ifelse(grepl("CGCNN", raw$proposal_source), "CGCNN", "CGCNN"), "\nK=", raw$K, ", a=", raw$alpha)
  methods <- c("raw top-K", "raw top-R", "split", "post-filter e", "e-BH", "PARC")
  ftr_cols <- c("raw_topK_FTR", "raw_topR_FTR", "split_conformal_FTR",
                "post_filter_e_threshold_FTR", "e_BH_full_pool_FTR", "PARC_FTR")
  rel_cols <- c("K", "PARC_release_size", "split_conformal_release_size",
                "post_filter_e_threshold_release_size", "e_BH_full_pool_release_size", "PARC_release_size")
  pieces <- list()
  for (i in seq_along(methods)) {
    z <- raw[, c("row", "K")]
    z$method <- methods[[i]]
    z$FTR <- raw[[ftr_cols[[i]]]]
    z$release_size <- raw[[rel_cols[[i]]]]
    z$release_fraction <- z$release_size / z$K
    pieces[[i]] <- z
  }
  dat <- do.call(rbind, pieces)
  dat$FTR[is.na(dat$FTR)] <- 0
  long <- long_rows(
    dat,
    c("row", "method"),
    c("FTR", "release_size", "release_fraction"),
    c(FTR = "FTR", release_size = "release size", release_fraction = "released/requested")
  )
  long$method <- factor(long$method, levels = methods)
  long$metric <- factor(long$metric, levels = c("FTR", "release size", "released/requested"))
  ggplot(long, aes(method, value, fill = method)) +
    geom_hline(data = data.frame(metric = "FTR", y = 0.10), aes(yintercept = y),
               inherit.aes = FALSE, linetype = "dashed", linewidth = 0.24, colour = "#606060") +
    geom_col(width = 0.72, colour = "white", linewidth = 0.08) +
    facet_grid(metric ~ row, scales = "free_y") +
    scale_fill_manual(values = c(
      "raw top-K" = unname(pal["baseline"]),
      "raw top-R" = "#D6E3ED",
      "split" = "#8E7CC3",
      "post-filter e" = "#4E79A7",
      "e-BH" = "#D9B36A",
      "PARC" = unname(pal["parc"])
    )) +
    labs(x = NULL, y = NULL, title = "Matched-volume and nearest-practical baseline frontier") +
    theme(axis.text.x = element_text(angle = 45, hjust = 1), legend.position = "none")
}

panel_c_gamma_grid <- function() {
  gamma <- read_table("materials_gamma_sensitivity_heatmap.csv")
  gamma$source <- source_label(gamma$proposal_source)
  gamma$release_fraction <- ifelse(gamma$K > 0, gamma$mean_release / gamma$K, 0)
  gamma$seed_fraction <- gamma$non_empty_seeds / gamma$seeds
  gamma$mass_log10 <- log10(pmax(gamma$best_mass_ratio_mean, 1e-3))
  long <- long_rows(
    gamma,
    c("source", "K", "gamma"),
    c("actual_FTR_mean", "release_fraction", "seed_fraction", "mass_log10"),
    c(
      actual_FTR_mean = "FTR",
      release_fraction = "released/requested",
      seed_fraction = "non-empty seeds",
      mass_log10 = "log10 mass ratio"
    )
  )
  long$metric <- factor(long$metric, levels = c("FTR", "released/requested", "non-empty seeds", "log10 mass ratio"))
  ggplot(long, aes(factor(gamma), factor(K), fill = value)) +
    geom_tile(colour = "white", linewidth = 0.12) +
    geom_text(aes(label = ifelse(metric == "FTR", sprintf("%.2f", value), sprintf("%.1f", value))),
              size = 1.35, colour = "#2D3642") +
    facet_grid(source ~ metric, scales = "free") +
    scale_fill_gradientn(colours = c("#F2F5F7", "#CFE3EC", "#7DB8CD", "#D98C80"), values = rescale(c(-1, 0, 0.1, 1)), guide = "none") +
    labs(x = "fixed gamma", y = "K", title = "Fixed-gamma sensitivity grid")
}

panel_d_block_refusal_controls <- function() {
  block <- read_table("table_materials_block_sensitivity.csv")
  random <- read_table("table_materials_random_score_control.csv")
  high <- read_table("table_materials_high_volume_refusal.csv")

  block$block <- gsub("_", " ", block$block_definition)
  block$release_fraction <- ifelse(block$K > 0, block$mean_release / block$K, 0)
  block$seed_fraction <- block$non_empty_seeds / block$seeds
  block$mass_log10 <- log10(pmax(block$best_mass_ratio_mean, 1e-3))
  block_long <- long_rows(
    block,
    c("block", "K"),
    c("actual_FTR_mean", "release_fraction", "seed_fraction", "mass_log10", "block_coverage_mean"),
    c(
      actual_FTR_mean = "FTR",
      release_fraction = "released/requested",
      seed_fraction = "non-empty seeds",
      mass_log10 = "log10 mass ratio",
      block_coverage_mean = "block coverage"
    )
  )
  p_block <- ggplot(block_long, aes(factor(K), value, group = block, colour = block)) +
    geom_hline(data = data.frame(metric = "FTR", y = 0.10), aes(yintercept = y),
               inherit.aes = FALSE, linetype = "dashed", linewidth = 0.24, colour = "#606060") +
    geom_line(linewidth = 0.32) +
    geom_point(size = 0.62) +
    facet_wrap(~metric, nrow = 1, scales = "free_y") +
    labs(x = "K", y = NULL, title = "block-definition sensitivity") +
    theme(axis.text.x = element_text(angle = 35, hjust = 1))

  random$control <- "random-score"
  high$control <- paste0("high-volume a=", high$alpha, ", rho=", high$rho)
  high <- high[high$K %in% c(1000, 5000), ]
  random$release_fraction <- ifelse(random$K > 0, random$mean_release / random$K, 0)
  high$release_fraction <- ifelse(high$K > 0, high$mean_release / high$K, 0)
  random$seed_fraction <- random$non_empty_seeds / random$seeds
  high$seed_fraction <- high$non_empty_seeds / high$seeds
  controls <- rbind(
    random[, c("control", "K", "actual_FTR_mean", "raw_topK_actual_FTR_mean", "release_fraction", "seed_fraction", "best_mass_ratio_mean")],
    high[, c("control", "K", "actual_FTR_mean", "raw_topK_actual_FTR_mean", "release_fraction", "seed_fraction", "best_mass_ratio_mean")]
  )
  controls$mass_log10 <- log10(pmax(controls$best_mass_ratio_mean, 1e-3))
  ctl_long <- long_rows(
    controls,
    c("control", "K"),
    c("actual_FTR_mean", "raw_topK_actual_FTR_mean", "release_fraction", "seed_fraction", "mass_log10"),
    c(
      actual_FTR_mean = "PARC FTR",
      raw_topK_actual_FTR_mean = "raw top-K FTR",
      release_fraction = "released/requested",
      seed_fraction = "non-empty seeds",
      mass_log10 = "log10 mass ratio"
    )
  )
  p_ctl <- ggplot(ctl_long, aes(factor(K), value, fill = control)) +
    geom_hline(data = data.frame(metric = c("PARC FTR", "raw top-K FTR"), y = 0.10),
               aes(yintercept = y), inherit.aes = FALSE, linetype = "dashed", linewidth = 0.24, colour = "#606060") +
    geom_col(position = position_dodge(width = 0.74), width = 0.62, colour = "white", linewidth = 0.08) +
    facet_wrap(~metric, nrow = 1, scales = "free_y") +
    scale_fill_manual(values = rep(c(unname(pal["random"]), unname(pal["baseline"]), unname(pal["alignn"]), unname(pal["parc"])), 5)) +
    labs(x = "K", y = NULL, title = "random and high-volume refusal controls") +
    theme(axis.text.x = element_text(angle = 35, hjust = 1), legend.position = "none")

  p_block / p_ctl + plot_layout(heights = c(1, 1))
}

main <- function() {
  save_panel(panel_a_threshold_surface(), "figure_5a_threshold_surface_grid", height_mm = 58)
  save_panel(panel_b_matched_baseline_grid(), "figure_5b_matched_baseline_grid", height_mm = 48)
  save_panel(panel_c_gamma_grid(), "figure_5c_gamma_sensitivity_grid", height_mm = 50)
  save_panel(panel_d_block_refusal_controls(), "figure_5d_block_refusal_control_grid", height_mm = 58)
}

main()

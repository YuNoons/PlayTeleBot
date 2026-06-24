use plotters::prelude::*;

pub struct SeriesStyling {
    pub color: String,
    pub thickness: u32,
}

pub struct Series {
    pub name: String,
    pub data: Vec<f64>,
    pub style: SeriesStyling,
}

pub struct PlotConfig {
    pub x_label: String,
    pub x_data: Vec<String>,
    pub series: Vec<Series>,
    pub bg_color: String,
    pub output_path: String,
}

pub fn parse_color(c: &str) -> Result<RGBColor, String> {
    let c_lower = c.trim().to_lowercase();
    match c_lower.as_str() {
        "red" => Ok(RED),
        "blue" => Ok(BLUE),
        "green" => Ok(GREEN),
        "yellow" => Ok(YELLOW),
        "cyan" => Ok(CYAN),
        "magenta" => Ok(MAGENTA),
        "black" => Ok(BLACK),
        "white" => Ok(WHITE),
        "gray" | "grey" => Ok(RGBColor(128, 128, 128)),
        hex if hex.starts_with('#') => {
            let hex_val = &hex[1..];
            if hex_val.len() >= 6 {
                let r = u8::from_str_radix(&hex_val[0..2], 16).map_err(|_| format!("Invalid HEX: {}", hex))?;
                let g = u8::from_str_radix(&hex_val[2..4], 16).map_err(|_| format!("Invalid HEX: {}", hex))?;
                let b = u8::from_str_radix(&hex_val[4..6], 16).map_err(|_| format!("Invalid HEX: {}", hex))?;
                Ok(RGBColor(r, g, b))
            } else {
                Err(format!("Invalid HEX: {}", hex))
            }
        },
        rgb if rgb.starts_with("rgb") => {
            let parts: Vec<&str> = rgb
                .trim_matches(|p| p == 'r' || p == 'g' || p == 'b' || p == 'a' || p == '(' || p == ')')
                .split(',')
                .collect();
            if parts.len() >= 3 {
                let r = parts[0].trim().parse::<u8>().unwrap_or(0);
                let g = parts[1].trim().parse::<u8>().unwrap_or(0);
                let b = parts[2].trim().parse::<u8>().unwrap_or(0);
                Ok(RGBColor(r, g, b))
            } else {
                Ok(BLACK)
            }
        }
        _ => Ok(BLACK),
    }
}

pub fn generate_plot(config: &PlotConfig) -> Result<(), Box<dyn std::error::Error>> {
    let root = BitMapBackend::new(&config.output_path, (1200, 800)).into_drawing_area();
    let bg = parse_color(&config.bg_color)?;
    root.fill(&bg)?;

    let is_dark_bg = (bg.0 as f32 * 0.299 + bg.1 as f32 * 0.587 + bg.2 as f32 * 0.114) < 128.0;
    let fg = if is_dark_bg { WHITE } else { BLACK };

    let mut min_y = f64::MAX;
    let mut max_y = f64::MIN;
    let mut has_data = false;

    for s in &config.series {
        for &val in &s.data {
            if val < min_y { min_y = val; }
            if val > max_y { max_y = val; }
            has_data = true;
        }
    }

    if !has_data {
        min_y = 0.0;
        max_y = 10.0;
    }

    let delta = (max_y - min_y).abs();
    let margin = if delta == 0.0 { 1.0 } else { delta * 0.2 };
    max_y += margin;
    min_y -= margin;

    let x_max = if config.x_data.is_empty() { 1.0 } else { (config.x_data.len() - 1) as f64 };

    let mut chart = ChartBuilder::on(&root)
        .caption(&config.x_label, ("sans-serif", 32).into_font().color(&fg))
        .margin(20)
        .x_label_area_size(40)
        .y_label_area_size(60)
        .build_cartesian_2d(0.0..x_max, min_y..max_y)?;

    chart
        .configure_mesh()
        .axis_desc_style(("sans-serif", 16).into_font().color(&fg))
        .label_style(("sans-serif", 16).into_font().color(&fg))
        .axis_style(&fg)
        .bold_line_style(fg.mix(0.1))
        .light_line_style(fg.mix(0.05))
        .x_label_formatter(&|x: &f64| {
            let idx = x.round() as usize;
            config.x_data.get(idx).map(|s| s.as_str()).unwrap_or("").to_string()
        })
        .x_labels(config.x_data.len())
        .draw()?;

    for s in &config.series {
        if s.data.is_empty() { continue; }

        let color = parse_color(&s.style.color)?;
        let thickness = s.style.thickness;
        let points: Vec<(f64, f64)> = s.data.iter().enumerate().map(|(i, &y)| (i as f64, y)).collect();

        // 1. Fill area
        chart.draw_series(AreaSeries::new(points.iter().copied(), min_y, color.mix(0.15)))?;

        // 2. Glow
        chart.draw_series(LineSeries::new(points.iter().copied(), color.mix(0.05).stroke_width(thickness + 12)))?;
        chart.draw_series(LineSeries::new(points.iter().copied(), color.mix(0.15).stroke_width(thickness + 4)))?;
        
        // 3. Main line
        chart
            .draw_series(LineSeries::new(points.iter().copied(), color.stroke_width(thickness)))?
            .label(&s.name)
            .legend(move |(x, y)| PathElement::new(vec![(x, y), (x + 20, y)], color.stroke_width(thickness)));
        
        // 4. Points
        chart.draw_series(PointSeries::of_element(
            points.iter().copied(),
            thickness as i32 + 5,
            color,
            &|c, size, _st| {
                EmptyElement::at(c)
                + Circle::new((0, 0), size, color.mix(0.25).filled())                 
                + Circle::new((0, 0), thickness as i32 + 2, bg.filled())              
                + Circle::new((0, 0), thickness as i32 + 2, color.stroke_width(2))    
            },
        ))?;
    }

    if !config.series.is_empty() && has_data {
        chart
            .configure_series_labels()
            .label_font(("sans-serif", 16).into_font().color(&fg))
            .background_style(bg.mix(0.8))
            .border_style(fg.mix(0.2))
            .position(SeriesLabelPosition::UpperRight)
            .draw()?;
    }

    root.present()?;
    Ok(())
}
